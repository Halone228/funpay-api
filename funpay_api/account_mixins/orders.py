from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional

from funpay_api.common import exceptions, utils
from .. import types

if TYPE_CHECKING:
    from funpay_api.async_account import AsyncAccount as Account


class OrdersMixin:
    async def send_review(self: Account, order_id: str, text: str, rating: Literal[1, 2, 3, 4, 5] = 5) -> str:
        """
        Отправляет / редактирует отзыв / ответ на отзыв.

        :param order_id: ID заказа.
        :type order_id: :obj:`str`

        :param text: текст отзыва.
        :type text: :obj:`str`

        :param rating: рейтинг (от 1 до 5).
        :type rating: :obj:`int`, опционально

        :return: ответ FunPay (HTML-код блока отзыва).
        :rtype: :obj:`str`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest"
        }
        text = text.strip()
        payload = {
            "authorId": self.id,
            "text": f"{text}{self.bot_character}" if text else text,
            "rating": rating,
            "csrf_token": self.csrf_token,
            "orderId": order_id
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.post("orders/review", headers=headers, data=payload)
        else:
            response = self.client.post("orders/review", headers=headers, data=payload)

        if response.status_code == 400:
            json_response = response.json()
            msg = json_response.get("msg")
            raise exceptions.FeedbackEditingError(response, msg, order_id)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        return response.json().get("content")

    async def delete_review(self: Account, order_id: str) -> str:
        """
        Удаляет отзыв / ответ на отзыв.

        :param order_id: ID заказа.
        :type order_id: :obj:`str`

        :return: ответ FunPay (HTML-код блока отзыва).
        :rtype: :obj:`str`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest"
        }
        payload = {
            "authorId": self.id,
            "csrf_token": self.csrf_token,
            "orderId": order_id
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.post("orders/reviewDelete", headers=headers, data=payload)
        else:
            response = self.client.post("orders/reviewDelete", headers=headers, data=payload)

        if response.status_code == 400:
            json_response = response.json()
            msg = json_response.get("msg")
            raise exceptions.FeedbackEditingError(response, msg, order_id)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        return response.json().get("content")

    async def refund(self: Account, order_id):
        """
        Оформляет возврат средств за заказ.

        :param order_id: ID заказа.
        :type order_id: :obj:`str`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }

        payload = {
            "id": order_id,
            "csrf_token": self.csrf_token
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.post("orders/refund", headers=headers, data=payload)
        else:
            response = self.client.post("orders/refund", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if response.json().get("error"):
            raise exceptions.RefundError(response, response.json().get("msg"), order_id)

    async def get_order_shortcut(self: Account, order_id: str) -> types.OrderShortcut:
        """
        Получает краткую информацию о заказе. РАБОТАЕТ ТОЛЬКО ДЛЯ ПРОДАЖ.

        :param order_id: ID заказа.
        :type order_id: :obj:`str`

        :return: объекст заказа.
        :rtype: :class:`funpay_api.types.OrderShortcut`
        """
        # todo взаимодействие с покупками
        sales = await self.get_sales(id=order_id)
        return self.runner.saved_orders.get(order_id, sales[1][0])

    async def get_order(self: Account, order_id: str, locale: Literal["ru", "en", "uk"] | None = None) -> types.Order:
        """
        Получает полную информацию о заказе.

        :param order_id: ID заказа.
        :type order_id: :obj:`str`

        :return: объекст заказа.
        :rtype: :class:`funpay_api.types.Order`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {
            "accept": "*/*"
        }
        if not locale:
            locale = self._order_parse_locale

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"orders/{order_id}/", headers=headers, locale=locale)
        else:
            response = self.client.get(f"orders/{order_id}/", headers=headers, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self._default_locale
        html_response = response.text

        from funpay_api.common.parser import parse_order
        return parse_order(html_response, self, order_id)

    async def get_sales(self: Account, start_from: str | None = None, include_paid: bool = True, include_closed: bool = True,
                  include_refunded: bool = True, exclude_ids: list[str] | None = None,
                  id: Optional[str] = None, buyer: Optional[str] = None,
                  state: Optional[Literal["closed", "paid", "refunded"]] = None, game: Optional[int] = None,
                  section: Optional[str] = None, server: Optional[int] = None,
                  side: Optional[int] = None, locale: Literal["ru", "en", "uk"] | None = None,
                  subcategories: dict[str, tuple[types.SubCategoryTypes, int]] | None = None, **more_filters) -> \
            tuple[str | None, list[types.OrderShortcut], Literal["ru", "en", "uk"],
            dict[str, types.SubCategory]]:
        """
        Получает и парсит список заказов со страницы https://funpay.com/orders/trade

        :param start_from: ID заказа, с которого начать список (ID заказа должен быть без '#'!).
        :type start_from: :obj:`str`

        :param include_paid: включить ли в список заказы, ожидающие выполнения?
        :type include_paid: :obj:`bool`, опционально

        :param include_closed: включить ли в список закрытые заказы?
        :type include_closed: :obj:`bool`, опционально

        :param include_refunded: включить ли в список заказы, за которые запрошен возврат средств?
        :type include_refunded: :obj:`bool`, опционально

        :param exclude_ids: исключить заказы с ID из списка (ID заказа должен быть без '#'!).
        :type exclude_ids: :obj:`list` of :obj:`str`, опционально

        :param id: ID заказа.
        :type id: :obj:`str`, опционально

        :param buyer: никнейм покупателя.
        :type buyer: :obj:`str`, опционально

        :param state: статус заказа.
        :type: :obj:`str` `paid`, `closed` or `refunded`, опционально

        :param game: ID игры.
        :type game: :obj:`int`, опционально

        :param section: ID категории в формате `<тип лота>-<ID категории>`.\n
            Типы лотов:\n
            * `lot` - стандартный лот (например: `lot-256`)\n
            * `chip` - игровая валюта (например: `chip-4471`)\n
        :type section: :obj:`str`, опционально

        :param server: ID сервера.
        :type server: :obj:`int`, опционально

        :param side: ID стороны (платформы).
        :type side: :obj:`int`, опционально.

        :param more_filters: доп. фильтры.

        :return: (ID след. заказа (для start_from), список заказов)
        :rtype: :obj:`tuple` (:obj:`str` or :obj:`None`, :obj:`list` of :class:`funpay_api.types.OrderShortcut`)
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        exclude_ids = exclude_ids or []
        _subcategories = more_filters.pop("sudcategories", None)
        subcategories = subcategories or _subcategories
        filters = {"id": id, "buyer": buyer, "state": state, "game": game, "section": section, "server": server,
                   "side": side}
        filters = {name: filters[name] for name in filters if filters[name]}
        filters.update(more_filters)

        link = "https://funpay.com/orders/trade?"
        for name in filters:
            link += f"{name}={filters[name]}&"
        link = link[:-1]

        if start_from:
            filters["continue"] = start_from

        locale = locale or self._profile_parse_locale
        if isinstance(self.client, AsyncClient):
            response = await self.client.post(link, data=filters, locale=locale) if start_from else await self.client.get(link, locale=locale)
        else:
            response = self.client.post(link, data=filters, locale=locale) if start_from else self.client.get(link, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if not start_from:
            self.locale = self._default_locale
        html_response = response.text

        from funpay_api.common.parser import parse_sales
        return parse_sales(html_response, self, include_paid, include_closed, include_refunded, exclude_ids, start_from)

    async def get_sells(self: Account, start_from: str | None = None, include_paid: bool = True, include_closed: bool = True,
                  include_refunded: bool = True, exclude_ids: list[str] | None = None,
                  id: Optional[str] = None, buyer: Optional[str] = None,
                  state: Optional[Literal["closed", "paid", "refunded"]] = None, game: Optional[int] = None,
                  section: Optional[str] = None, server: Optional[int] = None,
                  side: Optional[int] = None, **more_filters) -> tuple[str | None, list[types.OrderShortcut]]:
        """Эта функция вскоре будет удалена. Используйте Account.get_sales()."""
        start_from, orders, loc, subcs = await self.get_sales(start_from, include_paid, include_closed, include_refunded,
                                                        exclude_ids, id, buyer, state, game, section, server,
                                                        side, None, None, **more_filters)
        return start_from, orders
