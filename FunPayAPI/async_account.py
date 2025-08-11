from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Any, Optional, IO

import FunPayAPI.common.enums
from FunPayAPI.common.utils import parse_currency, RegularExpressions
from .types import PaymentMethod, CalcResult

if TYPE_CHECKING:
    from .updater.runner import Runner

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from loguru import logger
import random
import string
import json
import time
import re

from . import types
from .common import exceptions, utils, enums
from .client import SyncClient, AsyncClient

PRIVATE_CHAT_ID_RE = re.compile(r"users-\d+-\d+$")


from FunPayAPI.account_mixins.account import AccountMixin
from FunPayAPI.account_mixins.categories import CategoriesMixin
from FunPayAPI.account_mixins.chat import ChatMixin
from FunPayAPI.account_mixins.lots import LotsMixin
from FunPayAPI.account_mixins.orders import OrdersMixin
from FunPayAPI.account_mixins.wallet import WalletMixin


class AsyncAccount(LotsMixin, ChatMixin, OrdersMixin, CategoriesMixin, WalletMixin, AccountMixin):
    """
    Класс для управления аккаунтом FunPay.

    :param golden_key: токен (golden_key) аккаунта.
    :type golden_key: :obj:`str`

    :param user_agent: user-agent браузера, с которого был произведен вход в аккаунт.
    :type user_agent: :obj:`str`

    :param requests_timeout: тайм-аут ожидания ответа на запросы.
    :type requests_timeout: :obj:`int` or :obj:`float`

    :param proxy: прокси для запросов.
    :type proxy: :obj:`dict` {:obj:`str`: :obj:`str` or :obj:`None`

    :param locale: текущий язык аккаунта, опционально.
    :type locale: :obj:`Literal["ru", "en", "uk"]` or :obj:`None`
    """

    def __init__(self, golden_key: str, user_agent: str | None = None,
                 requests_timeout: int | float = 10, proxy: Optional[dict] = None,
                 locale: Literal["ru", "en", "uk"] | None = None):
        self.golden_key: str = golden_key
        """Токен (golden_key) аккаунта."""
        self.user_agent: str | None = user_agent
        """User-agent браузера, с которого был произведен вход в аккаунт."""

        self.client = AsyncClient(golden_key, user_agent, requests_timeout, proxy, locale)

        self.html: str | None = None
        """HTML основной страницы FunPay."""
        self.app_data: dict | None = None
        """Appdata."""
        self.id: int | None = None
        """ID аккаунта."""
        self.username: str | None = None
        """Никнейм аккаунта."""
        self.active_sales: int | None = None
        """Активные продажи."""
        self.active_purchases: int | None = None
        """Активные покупки."""
        self.last_429_err_time: float = 0
        """Время последнего возникновения 429 ошибки"""
        self.last_flood_err_time: float = 0
        """Время последнего возникновения ошибки \"Нельзя отправлять сообщения слишком часто.\""""
        self.last_multiuser_flood_err_time: float = 0
        """Время последнего возникновения ошибки \"Нельзя слишком часто отправлять сообщения разным пользователям.\""""
        self._locale: Literal["ru", "en", "uk"] | None = None
        """Текущий язык аккаунта."""
        self._default_locale: Literal["ru", "en", "uk"] | None = locale
        """Язык аккаунта по умолчанию."""
        self._profile_parse_locale: Literal["ru", "en", "uk"] | None = locale
        """Язык по умолчанию для Account.get_user()"""
        self._chat_parse_locale: Literal["ru", "en", "uk"] | None = None
        """Язык по умолчанию для Account.get_chat()"""
        # self._sales_parse_locale: Literal["ru", "en", "uk"] | None = locale #todo
        """Язык по умолчанию для Account.get_sales()"""
        self._order_parse_locale: Literal["ru", "en", "uk"] | None = None
        """Язык по умолчанию для Account.get_order()"""
        self._lots_parse_locale: Literal["ru", "en", "uk"] | None = None
        """Язык по умолчанию для Account.get_subcategory_public_lots()"""
        self._subcategories_parse_locale: Literal["ru", "en", "uk"] | None = None
        """Язык по для получения названий разделов."""
        self._set_locale: Literal["ru", "en", "uk"] | None = None
        """Язык, на который будет переведем аккаунт при следующем GET-запросе."""
        self.currency: FunPayAPI.types.Currency = FunPayAPI.types.Currency.UNKNOWN
        """Валюта аккаунта"""
        self.total_balance: int | None = None
        """Примерный общий баланс аккаунта в валюте аккаунта."""
        self.csrf_token: str | None = None
        """CSRF токен."""
        self.phpsessid: str | None = None
        """PHPSESSID сессии."""
        self.last_update: int | None = None
        """Последнее время обновления аккаунта."""

        self.interlocutor_ids: dict[int, int] = {}
        """{id чата: id собеседника}"""

        self._initiated: bool = False

        self._saved_chats: dict[int, types.ChatShortcut] = {}
        self.runner: Runner | None = None
        """Объект Runner'а."""
        self._logout_link: str | None = None
        """Ссылка для выхода с аккаунта"""
        self._categories: list[types.Category] = []
        self._sorted_categories: dict[int, types.Category] = {}

        self._subcategories: list[types.SubCategory] = []
        self._sorted_subcategories: dict[types.SubCategoryTypes, dict[int, types.SubCategory]] = {
            types.SubCategoryTypes.COMMON: {},
            types.SubCategoryTypes.CURRENCY: {}
        }

        self._bot_character = "⁡"
        """Если сообщение начинается с этого символа, значит оно отправлено ботом."""
        self._old_bot_character = "⁤"
        """Старое значение self._bot_character, для корректной маркировки отправки ботом старых сообщений"""

    async def get(self, update_phpsessid: bool = True) -> "AsyncAccount":
        """
        Получает / обновляет данные об аккаунте. Необходимо вызывать каждые 40-60 минут, дабы обновить
        :py:obj:`.Account.phpsessid`.

        :param update_phpsessid: обновить :py:obj:`.Account.phpsessid` или использовать старый.
        :type update_phpsessid: :obj:`bool`, опционально

        :return: объект аккаунта с обновленными данными.
        :rtype: :class:`FunPayAPI.account.Account`
        """
        if not self.is_initiated:
            self.locale = self._subcategories_parse_locale

        response = await self.client.get("https://funpay.com/")

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if not self.is_initiated:
            self.locale = self._default_locale

        html_response = response.text

        from .common.parser import parse_account_data
        parse_account_data(html_response, self)
        self._setup_categories(html_response)

        cookies = response.cookies
        if update_phpsessid or not self.phpsessid:
            self.phpsessid = cookies.get("PHPSESSID")
            self.client.phpsessid = self.phpsessid

        self.last_update = int(time.time())
        self.html = html_response
        self._initiated = True
        return self
