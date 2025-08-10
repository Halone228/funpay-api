from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from bs4 import BeautifulSoup
import re

from FunPayAPI.common import exceptions, types
from FunPayAPI.client import AsyncClient

if TYPE_CHECKING:
    from FunPayAPI.account import Account

PRIVATE_CHAT_ID_RE = re.compile(r"users-\d+-\d+$")


class AccountMixin:
    async def logout(self: Account) -> None:
        """
        Выходит с аккаунта FunPay (сбрасывает golden_key).
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if isinstance(self.client, AsyncClient):
            await self.client.get(self._logout_link, headers={"accept": "*/*"})
        else:
            self.client.get(self._logout_link, headers={"accept": "*/*"})

    @property
    def is_initiated(self: Account) -> bool:
        """
        Инициализирован ли класс :class:`FunPayAPI.account.Account` с помощью метода :meth:`FunPayAPI.account.Account.get`?

        :return: :obj:`True`, если да, :obj:`False`, если нет.
        :rtype: :obj:`bool`
        """
        return self.__initiated

    @staticmethod
    def parse_buyer_viewing(json_responce: dict) -> types.BuyerViewing:
        buyer_id = json_responce.get("id")
        if not json_responce["data"]:
            return types.BuyerViewing(buyer_id, None, None, None, None)

        tag = json_responce["tag"]
        html = json_responce["data"]["html"]
        if html:
            html = html["desktop"]
            element = BeautifulSoup(html, "lxml").find("a")
            link, text = element.get("href"), element.text
        else:
            html, link, text = None, None, None

        return types.BuyerViewing(buyer_id, link, text, tag, html)

    @staticmethod
    def chat_id_private(chat_id: int | str):
        return isinstance(chat_id, int) or PRIVATE_CHAT_ID_RE.fullmatch(chat_id)

    @property
    def bot_character(self: Account) -> str:
        return self.__bot_character

    @property
    def old_bot_character(self: Account) -> str:
        return self.__old_bot_character

    @property
    def locale(self: Account) -> Literal["ru", "en", "uk"] | None:
        return self.__locale

    @locale.setter
    def locale(self: Account, new_locale: Literal["ru", "en", "uk"]):
        if self.__locale != new_locale and new_locale in ("ru", "en", "uk"):
            self.__set_locale = new_locale

    async def get_user(
        self: Account, user_id: int, locale: Literal["ru", "en", "uk"] | None = None
    ) -> types.UserProfile:
        """
        Парсит страницу пользователя.

        :param user_id: ID пользователя.
        :type user_id: :obj:`int`

        :return: объект профиля пользователя.
        :rtype: :class:`FunPayAPI.types.UserProfile`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not locale:
            locale = self.__profile_parse_locale

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(
                f"users/{user_id}/", headers={"accept": "*/*"}, locale=locale
            )
        else:
            response = self.client.get(
                f"users/{user_id}/", headers={"accept": "*/*"}, locale=locale
            )

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self.__default_locale
        html_response = response.text

        from FunPayAPI.common.parser import parse_user_profile

        return parse_user_profile(html_response, self, user_id)
