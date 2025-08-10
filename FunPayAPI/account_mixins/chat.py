from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional, IO

from FunPayAPI.common import exceptions, utils
from .. import types
from FunPayAPI.client import AsyncClient
from bs4 import BeautifulSoup
from loguru import logger
import json
import time

if TYPE_CHECKING:
    from FunPayAPI.account import Account


class ChatMixin:
    async def get_chat_history(self: Account, chat_id: int | str, last_message_id: int = 99999999999999999999999,
                         interlocutor_username: Optional[str] = None, from_id: int = 0) -> list[types.Message]:
        """
        Получает историю указанного чата (до 100 последних сообщений).

        :param chat_id: ID чата (или его текстовое обозначение).
        :type chat_id: :obj:`int` or :obj:`str`

        :param last_message_id: ID сообщения, с которого начинать историю (фильтр FunPay).
        :type last_message_id: :obj:`int`

        :param interlocutor_username: никнейм собеседника. Не нужно указывать для получения истории публичного чата.
            Так же не обязательно, но желательно указывать для получения истории личного чата.
        :type interlocutor_username: :obj:`str` or :obj:`None`, опционально.

        :param from_id: все сообщения с ID < переданного не попадут в возвращаемый список сообщений.
        :type from_id: :obj:`int`, опционально.

        :return: история указанного чата.
        :rtype: :obj:`list` of :class:`FunPayAPI.types.Message`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest"
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"chat/history?node={chat_id}&last_message={last_message_id}", headers=headers)
        else:
            response = self.client.get(f"chat/history?node={chat_id}&last_message={last_message_id}", headers=headers)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        from FunPayAPI.common.parser import parse_chat_history
        return parse_chat_history(json_response, self, chat_id, interlocutor_username, from_id)

    async def get_chats_histories(self: Account, chats_data: dict[int | str, str | None],
                            interlocutor_ids: list[int] | None = None) -> dict[int, list[types.Message]]:
        """
        Получает историю сообщений сразу нескольких чатов
        (до 50 сообщений на личный чат, до 25 сообщений на публичный чат).
        Прокидывает в Account.runner информацию о том, какие лоты смотрят cобеседники (interlocutor_ids).

        :param chats_data: ID чатов и никнеймы собеседников (None, если никнейм неизвестен)\n
            Например: {48392847: "SLLMK", 58392098: "Amongus", 38948728: None}
        :type chats_data: :obj:`dict` {:obj:`int` or :obj:`str`: :obj:`str` or :obj:`None`}

        :return: словарь с историями чатов в формате {ID чата: [список сообщений]}
        :rtype: :obj:`dict` {:obj:`int`: :obj:`list` of :class:`FunPayAPI.types.Message`}
        """
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        chats = [{"type": "chat_node", "id": i, "tag": "00000000",
                  "data": {"node": i, "last_message": -1, "content": ""}} for i in chats_data]
        buyers = [{"type": "c-p-u",
                   "id": str(buyer),
                   "tag": utils.random_tag(),
                   "data": False} for buyer in interlocutor_ids or []]
        payload = {
            "objects": json.dumps([*chats, *buyers]),
            "request": False,
            "csrf_token": self.csrf_token
        }
        if isinstance(self.client, AsyncClient):
            response = await self.client.post("runner/", headers=headers, data=payload)
        else:
            response = self.client.post("runner/", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()

        from FunPayAPI.common.parser import parse_chats_histories
        return parse_chats_histories(json_response, self, chats_data)

    async def upload_image(self: Account, image: str | IO[bytes], type_: Literal["chat", "offer"] = "chat") -> int:
        """
        Выгружает изображение на сервер FunPay для дальнейшей отправки в качестве сообщения.
        Для отправки изображения в чат рекомендуется использовать метод :meth:`FunPayAPI.account.Account.send_image`.

        :param image: путь до изображения или представление изображения в виде байтов.
        :type image: :obj:`str` or :obj:`bytes`

        :param type_: куда грузим изображение? ("chat" / "offer").
        :type type_: :obj:`str` `chat` or `offer`

        :return: ID изображения на серверах FunPay.
        :rtype: :obj:`int`
        """

        assert type_ in ("chat", "offer")

        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if isinstance(image, str):
            files = {'file': image}
        else:
            files = {'file': image.read()}

        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest",
        }
        # file/addChatImage, file/addOfferImage
        if isinstance(self.client, AsyncClient):
            response = await self.client.post(f"file/add{type_.title()}Image", headers=headers, files=files)
        else:
            response = self.client.post(f"file/add{type_.title()}Image", headers=headers, files=files)

        if response.status_code == 400:
            try:
                json_response = response.json()
                message = json_response.get("msg")
                raise exceptions.ImageUploadError(response, message)
            except Exception:
                raise exceptions.ImageUploadError(response, None)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if not (document_id := response.json().get("fileId")):
            raise exceptions.ImageUploadError(response, None)
        return int(document_id)

    async def send_message(self: Account, chat_id: int | str, text: Optional[str] = None, chat_name: Optional[str] = None,
                     interlocutor_id: Optional[int] = None,
                     image_id: Optional[int] = None, add_to_ignore_list: bool = True,
                     update_last_saved_message: bool = False, leave_as_unread: bool = False) -> types.Message:
        """
        Отправляет сообщение в чат.

        :param chat_id: ID чата.
        :type chat_id: :obj:`int` or :obj:`str`

        :param text: текст сообщения.
        :type text: :obj:`str` or :obj:`None`, опционально

        :param chat_name: название чата (для возвращаемого объекта сообщения) (не нужно для отправки сообщения в публичный чат).
        :type chat_name: :obj:`str` or :obj:`None`, опционально

        :param interlocutor_id: ID собеседника (не нужно для отправки сообщения в публичный чат).
        :type interlocutor_id: :obj:`int` or :obj:`None`, опционально

        :param image_id: ID изображения. Доступно только для личных чатов.
        :type image_id: :obj:`int` or :obj:`None`, опционально

        :param add_to_ignore_list: добавлять ли ID отправленного сообщения в игнорируемый список Runner'а?
        :type add_to_ignore_list: :obj:`bool`, опционально

        :param update_last_saved_message: обновлять ли последнее сохраненное сообщение на отправленное в Runner'е?
        :type update_last_saved_message: :obj:`bool`, опционально.

        :param leave_as_unread: оставлять ли сообщение непрочитанным при отправке?
        :type leave_as_unread: :obj:`bool`, опционально

        :return: экземпляр отправленного сообщения.
        :rtype: :class:`FunPayAPI.types.Message`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        request = {
            "action": "chat_message",
            "data": {"node": chat_id, "last_message": -1, "content": text}
        }

        if image_id is not None:
            request["data"]["image_id"] = image_id
            request["data"]["content"] = ""
        else:
            request["data"]["content"] = f"{self.bot_character}{text}" if text else ""

        objects = [
            {
                "type": "chat_node",
                "id": chat_id,
                "tag": "00000000",
                "data": {"node": chat_id, "last_message": -1, "content": ""}
            }
        ]
        payload = {
            "objects": "" if leave_as_unread else json.dumps(objects),
            "request": json.dumps(request),
            "csrf_token": self.csrf_token
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.post("runner/", headers=headers, data=payload)
        else:
            response = self.client.post("runner/", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        if not (resp := json_response.get("response")):
            raise exceptions.MessageNotDeliveredError(response, None, chat_id)

        if (error_text := resp.get("error")) is not None:
            if error_text in ("Нельзя отправлять сообщения слишком часто.",
                              "You cannot send messages too frequently.",
                              "Не можна надсилати повідомлення занадто часто."):
                self.last_flood_err_time = time.time()
            elif error_text in ("Нельзя слишком часто отправлять сообщения разным пользователям.",
                                "Не можна надто часто надсилати повідомлення різним користувачам.",
                                "You cannot message multiple users too frequently."):
                self.last_multiuser_flood_err_time = time.time()
            raise exceptions.MessageNotDeliveredError(response, error_text, chat_id)
        if leave_as_unread:
            message_text = text
            fake_html = f"""
            <div class="chat-msg-item" id="message-0000000000">
                <div class="chat-message">
                    <div class="chat-msg-body">
                        <div class="chat-msg-text">{message_text}</div>
                    </div>
                </div>
            </div>
            """
            message_obj = types.Message(0, message_text, chat_id, chat_name, interlocutor_id, self.username, self.id,
                                        fake_html, None,
                                        None)
        else:
            mes = json_response["objects"][0]["data"]["messages"][-1]
            parser = BeautifulSoup(mes["html"].replace("<br>", "\n"), "lxml")
            image_name = None
            image_link = None
            message_text = None
            try:
                if image_tag := parser.find("a", {"class": "chat-img-link"}):
                    image_name = image_tag.find("img")
                    image_name = image_name.get('alt') if image_name else None
                    image_link = image_tag.get("href")
                else:
                    message_text = parser.find("div", {"class": "chat-msg-text"}).text. \
                        replace(self.bot_character, "", 1)
            except Exception as e:
                logger.debug("SEND_MESSAGE RESPONSE")
                logger.debug(response.content.decode())
                raise e
            message_obj = types.Message(int(mes["id"]), message_text, chat_id, chat_name, interlocutor_id,
                                        self.username, self.id,
                                        mes["html"], image_link, image_name)
        if self.runner and isinstance(chat_id, int):
            if add_to_ignore_list and message_obj.id:
                self.runner.mark_as_by_bot(chat_id, message_obj.id)
            if update_last_saved_message:
                self.runner.update_last_message(chat_id, message_obj.id, message_obj.text)
        return message_obj

    async def send_image(self: Account, chat_id: int, image: int | str | IO[bytes], chat_name: Optional[str] = None,
                   interlocutor_id: Optional[int] = None,
                   add_to_ignore_list: bool = True, update_last_saved_message: bool = False,
                   leave_as_unread: bool = False) -> types.Message:
        """
        Отправляет изображение в чат. Доступно только для личных чатов.

        :param chat_id: ID чата.
        :type chat_id: :obj:`int`

        :param image: ID изображения / путь до изображения / изображение в виде байтов.
            Если передан путь до изображения или представление изображения в виде байтов, сначала оно будет выгружено
            с помощью метода :meth:`FunPayAPI.account.Account.upload_image`.
        :type image: :obj:`int` or :obj:`str` or :obj:`bytes`

        :param chat_name: Название чата (никнейм собеседника). Нужен для возвращаемого объекта.
        :type chat_name: :obj:`str` or :obj:`None`, опционально

        :param interlocutor_id: ID собеседника (не нужно для отправки сообщения в публичный чат).
        :type interlocutor_id: :obj:`int` or :obj:`None`, опционально

        :param add_to_ignore_list: добавлять ли ID отправленного сообщения в игнорируемый список Runner'а?
        :type add_to_ignore_list: :obj:`bool`, опционально

        :param update_last_saved_message: обновлять ли последнее сохраненное сообщение на отправленное в Runner'е?
        :type update_last_saved_message: :obj:`bool`, опционально

        :param leave_as_unread: оставлять ли сообщение непрочитанным при отправке?
        :type leave_as_unread: :obj:`bool`, опционально

        :return: объект отправленного сообщения.
        :rtype: :class:`FunPayAPI.types.Message`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if not isinstance(image, int):
            image = await self.upload_image(image, type_="chat")
        result = await self.send_message(chat_id, None, chat_name, interlocutor_id,
                                   image, add_to_ignore_list, update_last_saved_message,
                                   leave_as_unread)
        return result

    async def request_chats(self: Account) -> list[types.ChatShortcut]:
        """
        Запрашивает чаты и парсит их.

        :return: объекты чатов (не больше 50).
        :rtype: :obj:`list` of :class:`FunPayAPI.types.ChatShortcut`
        """
        chats = {
            "type": "chat_bookmarks",
            "id": self.id,
            "tag": utils.random_tag(),
            "data": False
        }
        payload = {
            "objects": json.dumps([chats]),
            "request": False,
            "csrf_token": self.csrf_token
        }
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        if isinstance(self.client, AsyncClient):
            response = await self.client.post("https://funpay.com/runner/", headers=headers, data=payload)
        else:
            response = self.client.post("https://funpay.com/runner/", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()

        msgs = ""
        for obj in json_response["objects"]:
            if obj.get("type") != "chat_bookmarks":
                continue
            msgs = obj["data"]["html"]
        if not msgs:
            return []

        from FunPayAPI.common.parser import parse_chats
        return parse_chats(msgs, self)

    async def get_chats(self: Account, update: bool = False) -> dict[int, types.ChatShortcut]:
        """
        Возвращает словарь с сохраненными чатами ({id: types.ChatShortcut})

        :param update: обновлять ли предварительно список чатов с помощью доп. запроса?
        :type update: :obj:`bool`, опционально

        :return: словарь с сохраненными чатами.
        :rtype: :obj:`dict` {:obj:`int`: :class:`FunPayAPi.types.ChatShortcut`}
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if update:
            chats = await self.request_chats()
            self.add_chats(chats)
        return self._saved_chats

    async def get_chat_by_name(self: Account, name: str, make_request: bool = False) -> types.ChatShortcut | None:
        """
        Возвращает чат по его названию (если он сохранен).

        :param name: название чата.
        :type name: :obj:`str`

        :param make_request: обновить ли сохраненные чаты, если чат не был найден?
        :type make_request: :obj:`bool`, опционально

        :return: объект чата или :obj:`None`, если чат не был найден.
        :rtype: :class:`FunPayAPI.types.ChatShortcut` or :obj:`None`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        for i in self._saved_chats:
            if self._saved_chats[i].name == name:
                return self._saved_chats[i]

        if make_request:
            self.add_chats(await self.request_chats())
            return await self.get_chat_by_name(name)
        else:
            return None

    async def get_chat_by_id(self: Account, chat_id: int, make_request: bool = False) -> types.ChatShortcut | None:
        """
        Возвращает личный чат по его ID (если он сохранен).

        :param chat_id: ID чата.
        :type chat_id: :obj:`int`

        :param make_request: обновить ли сохраненные чаты, если чат не был найден?
        :type make_request: :obj:`bool`, опционально

        :return: объект чата или :obj:`None`, если чат не был найден.
        :rtype: :class:`FunPayAPI.types.ChatShortcut` or :obj:`None`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if not make_request or chat_id in self._saved_chats:
            return self._saved_chats.get(chat_id)

        self.add_chats(await self.request_chats())
        return await self.get_chat_by_id(chat_id)

    async def get_chat(self: Account, chat_id: int, with_history: bool = True,
                 locale: Literal["ru", "en", "uk"] | None = None) -> types.Chat:
        """
        Получает информацию о личном чате.

        :param chat_id: ID чата.
        :type chat_id: :obj:`int`

        :param with_history: получать ли историю сообщений?.
        :type with_history: :obj:`bool`

        :return: объект чата.
        :rtype: :class:`FunPayAPI.types.Chat`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if not locale:
            locale = self._chat_parse_locale

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"chat/?node={chat_id}", headers={"accept": "*/*"}, locale=locale)
        else:
            response = self.client.get(f"chat/?node={chat_id}", headers={"accept": "*/*"}, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self._default_locale
        html_response = response.text

        from FunPayAPI.common.parser import parse_chat
        return parse_chat(html_response, self, chat_id, with_history)

    def add_chats(self: Account, chats: list[types.ChatShortcut]):
        """
        Сохраняет чаты.

        :param chats: объекты чатов.
        :type chats: :obj:`list` of :class:`FunPayAPI.types.ChatShortcut`
        """
        for i in chats:
            self._saved_chats[i.id] = i
