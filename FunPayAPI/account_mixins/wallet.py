from __future__ import annotations
from typing import TYPE_CHECKING

from FunPayAPI.common import enums, utils, exceptions
from .. import types
from FunPayAPI.common.utils import RegularExpressions, parse_currency
from bs4 import BeautifulSoup
import json
from bs4 import BeautifulSoup
import json

if TYPE_CHECKING:
    from FunPayAPI.async_account import AsyncAccount as Account


class WalletMixin:
    async def withdraw(self: Account, currency: enums.Currency, wallet: enums.Wallet, amount: int | float, address: str) -> float:
        """
        Отправляет запрос на вывод средств.

        :param currency: валюта.
        :type currency: :class:`FunPayAPI.common.enums.Currency`

        :param wallet: тип кошелька.
        :type wallet: :class:`FunPayAPI.common.enums.Wallet`

        :param amount: кол-во средств.
        :type amount: :obj:`int` or :obj:`float`

        :param address: адрес кошелька.
        :type address: :obj:`str`

        :return: кол-во выведенных средств с учетом комиссии FunPay.
        :rtype: :obj:`float`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        wallets = {
            enums.Wallet.QIWI: "qiwi",
            enums.Wallet.YOUMONEY: "fps",
            enums.Wallet.BINANCE: "binance",
            enums.Wallet.TRC: "usdt_trc",
            enums.Wallet.CARD_RUB: "card_rub",
            enums.Wallet.CARD_USD: "card_usd",
            enums.Wallet.CARD_EUR: "card_eur",
            enums.Wallet.WEBMONEY: "wmz"
        }
        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest"
        }
        payload = {
            "csrf_token": self.csrf_token,
            "currency_id": currency.code,
            "ext_currency_id": wallets[wallet],
            "wallet": address,
            "amount_int": str(amount)
        }
        if isinstance(self.client, AsyncClient):
            response = await self.client.post("withdraw/withdraw", headers=headers, data=payload)
        else:
            response = self.client.post("withdraw/withdraw", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        if json_response.get("error"):
            error_message = json_response.get("msg")
            raise exceptions.WithdrawError(response, error_message)
        return float(json_response.get("amount_ext"))

    async def get_balance(self: Account, lot_id: int) -> types.Balance:
        """
        Получает информацию о балансе пользователя.

        :param lot_id: ID лота, на котором проверять баланс.
        :type lot_id: :obj:`int`, опционально

        :return: информацию о балансе пользователя.
        :rtype: :class:`FunPayAPI.types.Balance`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"lots/offer?id={lot_id}", headers={"accept": "*/*"})
        else:
            response = self.client.get(f"lots/offer?id={lot_id}", headers={"accept": "*/*"})

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        html_response = response.text

        from FunPayAPI.common.parser import parse_balance
        return parse_balance(html_response, self)

    async def calc(self: Account, subcategory_type: enums.SubCategoryTypes, subcategory_id: int | None = None,
             game_id: int | None = None, price: int | float = 1000):
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        if subcategory_type == types.SubCategoryTypes.COMMON:
            key = "nodeId"
            type_ = "lots"
            value = subcategory_id
        else:
            key = "game"
            type_ = "chips"
            value = game_id

        assert value is not None

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }

        if isinstance(self.client, AsyncClient):
            r = await self.client.post(f"{type_}/calc", headers=headers, data={key: value, "price": price})
        else:
            r = self.client.post(f"{type_}/calc", headers=headers, data={key: value, "price": price})

        if r.status_code != 200:
            raise exceptions.RequestFailedError(r)

        json_resp = r.json()
        if (error := json_resp.get("error")):
            raise Exception(f"Произошел бабах, не нашелся ответ: {error}")  # todo
        methods = []
        for method in json_resp.get("methods"):
            methods.append(PaymentMethod(method.get("name"), float(method["price"].replace(" ", "")),
                                         parse_currency(method.get("unit")), method.get("sort")))
        if "minPrice" in json_resp:
            min_price, min_price_currency = json_resp["minPrice"].rsplit(" ", maxsplit=1)
            min_price = float(min_price.replace(" ", ""))
            min_price_currency = parse_currency(min_price_currency)
        else:
            min_price, min_price_currency = None, types.Currency.UNKNOWN
        return CalcResult(subcategory_type, subcategory_id, methods, price, min_price, min_price_currency,
                          self.currency)

    async def get_exchange_rate(self: Account, currency: types.Currency) -> tuple[float, types.Currency]:
        """
        Получает курс обмена текущей валюты аккаунта на переданную, обновляет валюту аккаунта.
        Возвращает X, где X <currency> = 1 <валюта аккаунта> и текущую валюту аккаунта.

        :param currency: Валюта, на которую нужно получить курс обмена.
        :type currency: :obj:`types.Currency`

        :return: Кортеж, содержащий коэффициент обмена и текущую валюту аккаунта.
        :rtype: :obj:`tuple[float, types.Currency]`
        """
        if isinstance(self.client, AsyncClient):
            r = await self.client.post("https://funpay.com/account/switchCurrency",
                                 headers={"accept": "*/*", "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                                          "x-requested-with": "XMLHttpRequest"},
                                 data={"cy": currency.code, "csrf_token": self.csrf_token, "confirmed": "false"})
        else:
            r = self.client.post("https://funpay.com/account/switchCurrency",
                                 headers={"accept": "*/*", "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                                          "x-requested-with": "XMLHttpRequest"},
                                 data={"cy": currency.code, "csrf_token": self.csrf_token, "confirmed": "false"})
        if r.status_code != 200:
            raise exceptions.RequestFailedError(r)

        b = json.loads(r.text)
        if "url" in b and not b["url"]:
            self.currency = currency
            return 1, currency
        else:
            s = BeautifulSoup(b["modal"], "lxml").find("p", class_="lead").text.replace("\xa0", " ")
            match = RegularExpressions().EXCHANGE_RATE.fullmatch(s)
            assert match is not None
            swipe_to = match.group(2)
            assert swipe_to.lower() == currency.code
            price1 = float(match.group(4))
            currency1 = parse_currency(match.group(5))
            price2 = float(match.group(7))
            currency2 = parse_currency(match.group(8))
            now_currency = ({currency1, currency2} - {currency, }).pop()
            self.currency = now_currency
            if now_currency == currency1:
                return price2 / price1, now_currency
            else:
                return price1 / price2, now_currency
