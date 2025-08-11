from __future__ import annotations
from typing import TYPE_CHECKING, Literal

from ..common import exceptions, enums
from .. import types

if TYPE_CHECKING:
    from FunPayAPI.async_account import AsyncAccount as Account


class LotsMixin:
    async def get_subcategory_public_lots(self: Account, subcategory_type: enums.SubCategoryTypes, subcategory_id: int,
                                    locale: Literal["ru", "en", "uk"] | None = None) -> list[types.LotShortcut]:
        """
        Получает список всех опубликованных лотов переданной подкатегории.

        :param subcategory_type: тип подкатегории.
        :type subcategory_type: :class:`FunPayAPI.enums.SubCategoryTypes`

        :param subcategory_id: ID подкатегории.
        :type subcategory_id: :obj:`int`

        :return: список всех опубликованных лотов переданной подкатегории.
        :rtype: :obj:`list` of :class:`FunPayAPI.types.LotShortcut`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()

        meth = f"lots/{subcategory_id}/" if subcategory_type is enums.SubCategoryTypes.COMMON else f"chips/{subcategory_id}/"
        if not locale:
            locale = self._lots_parse_locale

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(meth, headers={"accept": "*/*"}, locale=locale)
        else:
            response = self.client.get(meth, headers={"accept": "*/*"}, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self._default_locale
        html_response = response.text

        from ..common.parser import parse_subcategory_public_lots
        return parse_subcategory_public_lots(html_response, self, subcategory_type, subcategory_id)

    async def get_my_subcategory_lots(self: Account, subcategory_id: int,
                                locale: Literal["ru", "en", "uk"] | None = None) -> list[types.MyLotShortcut]:
        """
        :param subcategory_id: ID подкатегории.
        :type subcategory_id: :obj:`int`

        :return: список лотов переданной подкатегории на аккаунте.
        :rtype: :obj:`list` of :class:`FunPayAPI.types.MyLotShortcut`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        meth = f"lots/{subcategory_id}/trade"
        if not locale:
            locale = self._lots_parse_locale

        if isinstance(self.client, AsyncClient):
            response = await self.client.get(meth, headers={"accept": "*/*"}, locale=locale)
        else:
            response = self.client.get(meth, headers={"accept": "*/*"}, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self._default_locale
        html_response = response.text

        from ..common.parser import parse_my_subcategory_lots
        return parse_my_subcategory_lots(html_response, self, subcategory_id)

    async def get_lot_page(self: Account, lot_id: int, locale: Literal["ru", "en", "uk"] | None = None):
        """
        Возвращает страницу лота.

        :param lot_id: ID лота.
        :type lot_id: :obj:`int` or :obj:`str`

        :return: объект страницы лота или :obj:`None`, если лот не найден.
        :rtype: :class:`FunPayAPI.types.lotPage` or :obj:`None`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {
            "accept": "*/*"
        }
        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"lots/offer?id={lot_id}", headers=headers, locale=locale)
        else:
            response = self.client.get(f"lots/offer?id={lot_id}", headers=headers, locale=locale)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        if locale:
            self.locale = self._default_locale
        html_response = response.text

        from ..common.parser import parse_lot_page
        return parse_lot_page(html_response, self, lot_id)

    async def get_lot_fields(self: Account, lot_id: int) -> types.LotFields:
        """
        Получает все поля лота.

        :param lot_id: ID лота.
        :type lot_id: :obj:`int`

        :return: объект с полями лота.
        :rtype: :class:`FunPayAPI.types.LotFields`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {}
        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"lots/offerEdit?offer={lot_id}", headers=headers)
        else:
            response = self.client.get(f"lots/offerEdit?offer={lot_id}", headers=headers)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        html_response = response.text
        bs = BeautifulSoup(html_response, "lxml")
        error_message = bs.find("p", class_="lead")
        if error_message:
            raise exceptions.LotParsingError(response, error_message.text, lot_id)
        result = {}
        result.update({field["name"]: field.get("value") or "" for field in bs.find_all("input")})
        result.update({field["name"]: field.text or "" for field in bs.find_all("textarea")})
        result.update({
            field["name"]: field.find("option", selected=True)["value"]
            for field in bs.find_all("select") if
            "hidden" not in field.find_parent(class_="form-group").get("class", [])
        })
        result.update({field["name"]: "on" for field in bs.find_all("input", {"type": "checkbox"}, checked=True)})
        subcategory = self.get_subcategory(enums.SubCategoryTypes.COMMON, int(result.get("node_id", 0)))
        self.csrf_token = result.get("csrf_token") or self.csrf_token
        currency = utils.parse_currency(bs.find("span", class_="form-control-feedback").text)
        if self.currency != currency:
            self.currency = currency
        bs_buyer_prices = bs.find("table", class_="table-buyers-prices").find_all("tr")
        payment_methods = []
        for i, pm in enumerate(bs_buyer_prices):
            pm_price, pm_currency = pm.find("td").text.rsplit(maxsplit=1)
            pm_price = float(pm_price.replace(" ", ""))
            pm_currency = utils.parse_currency(pm_currency)
            payment_methods.append(types.PaymentMethod(pm.find("th").text, pm_price, pm_currency, i))
        calc_result = types.CalcResult(types.SubCategoryTypes.COMMON, subcategory.id, payment_methods,
                                 float(result["price"]), None, types.Currency.UNKNOWN, currency)
        return types.LotFields(lot_id, result, subcategory, currency, calc_result)

    async def get_chip_fields(self: Account, subcategory_id: int) -> types.ChipFields:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {}
        if isinstance(self.client, AsyncClient):
            response = await self.client.get(f"chips/{subcategory_id}/trade", headers=headers)
        else:
            response = self.client.get(f"chips/{subcategory_id}/trade", headers=headers)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        html_response = response.text
        bs = BeautifulSoup(html_response, "lxml")
        result = {field["name"]: field.get("value") or "" for field in bs.find_all("input") if field["name"] != "query"}
        result.update({field["name"]: "on" for field in bs.find_all("input", {"type": "checkbox"}, checked=True)})
        return types.ChipFields(self.id, subcategory_id, result)

    async def save_offer(self: Account, offer_fields: types.LotFields | types.ChipFields):
        """
        Сохраняет лот на FunPay.

        :param offer_fields: объект с полями лота.
        :type offer_fields: :class:`FunPayAPI.types.LotFields`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        offer_fields.csrf_token = self.csrf_token

        if isinstance(offer_fields, types.LotFields):
            id_ = offer_fields.lot_id
            fields = offer_fields.renew_fields().fields
            fields["location"] = "trade"
            api_method = "lots/offerSave"
        else:
            id_ = offer_fields.subcategory_id
            fields = offer_fields.renew_fields().fields
            api_method = "chips/saveOffers"

        if isinstance(self.client, AsyncClient):
            response = await self.client.post(api_method, headers=headers, data=fields)
        else:
            response = self.client.post(api_method, headers=headers, data=fields)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        errors_dict = {}
        if (errors := json_response.get("errors")) or json_response.get("error"):
            if errors:
                for k, v in errors:
                    errors_dict.update({k: v})

            raise exceptions.LotSavingError(response, json_response.get("error"), id_, errors_dict)

    async def save_chip(self: Account, chip_fields: types.ChipFields):
        await self.save_offer(chip_fields)

    async def save_lot(self: Account, lot_fields: types.LotFields):
        await self.save_offer(lot_fields)

    async def delete_lot(self: Account, lot_id: int) -> None:
        """
        Удаляет лот.

        :param lot_id: ID лота.
        :type lot_id: :obj:`int`
        """
        await self.save_lot(types.LotFields(lot_id, {"csrf_token": self.csrf_token, "offer_id": lot_id, "deleted": "1"}))

    async def get_raise_modal(self: Account, category_id: int) -> dict:
        """
        Отправляет запрос на получение modal-формы для поднятия лотов категории (игры).
        !ВНИМАНИЕ! Если на аккаунте только 1 подкатегория, относящаяся переданной категории (игре),
        то FunPay поднимет лоты данной подкатегории без отправления modal-формы с выбором других подкатегорий.

        :param category_id: ID категории (игры).
        :type category_id: :obj:`int`

        :return: ответ FunPay.
        :rtype: :obj:`dict`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        category = self.get_category(category_id)
        subcategory = category.get_subcategories()[0]
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        payload = {
            "game_id": category_id,
            "node_id": subcategory.id
        }
        if isinstance(self.client, AsyncClient):
            response = await self.client.post("https://funpay.com/lots/raise", headers=headers, data=payload)
        else:
            response = self.client.post("https://funpay.com/lots/raise", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        return json_response

    async def raise_lots(self: Account, category_id: int, subcategories: Optional[list[int | types.SubCategory]] = None,
                   exclude: list[int] | None = None) -> bool:
        """
        Поднимает все лоты всех подкатегорий переданной категории (игры).

        :param category_id: ID категории (игры).
        :type category_id: :obj:`int`

        :param subcategories: список подкатегорий, которые необходимо поднять. Если не указаны, поднимутся все
            подкатегории переданной категории.
        :type subcategories: :obj:`list` of :obj:`int` or :class:`FunPayAPI.types.SubCategory`

        :param exclude: ID подкатегорий, которые не нужно поднимать.
        :type exclude: :obj:`list` of :obj:`int`, опционально.

        :return: `True`
        :rtype: :obj:`bool`
        """
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not (category := self.get_category(category_id)):
            raise Exception("Not Found")  # todo

        exclude = exclude or []
        if subcategories:
            subcats = []
            for i in subcategories:
                if isinstance(i, types.SubCategory):
                    if i.type is types.SubCategoryTypes.COMMON and i.category.id == category.id and i.id not in exclude:
                        subcats.append(i)
                else:
                    if not (subcat := category.get_subcategory(types.SubCategoryTypes.COMMON, i)):
                        continue
                    subcats.append(subcat)
        else:
            subcats = [i for i in category.get_subcategories() if
                       i.type is types.SubCategoryTypes.COMMON and i.id not in exclude]

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest"
        }
        payload = {
            "game_id": category_id,
            "node_id": subcats[0].id,
            "node_ids[]": [i.id for i in subcats]
        }

        if isinstance(self.client, AsyncClient):
            response = await self.client.post("lots/raise", headers=headers, data=payload)
        else:
            response = self.client.post("lots/raise", headers=headers, data=payload)

        if response.status_code != 200:
            raise exceptions.RequestFailedError(response)

        json_response = response.json()
        logger.debug(f"Ответ FunPay (поднятие категорий): {json_response}.")  # locale
        if not json_response.get("error") and not json_response.get("url"):
            return True
        elif json_response.get("url"):
            raise exceptions.RaiseError(response, category.name, json_response.get("url"), 7200)
        elif json_response.get("error") and json_response.get("msg") and \
                any([i in json_response.get("msg") for i in ("Подождите ", "Please wait ", "Зачекайте ")]):
            wait_time = utils.parse_wait_time(json_response.get("msg"))
            raise exceptions.RaiseError(response, category.name, json_response.get("msg"), wait_time)
        else:
            raise exceptions.RaiseError(response, category.name, json_response.get("msg"), None)
