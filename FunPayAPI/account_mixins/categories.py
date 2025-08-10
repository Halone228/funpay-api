from __future__ import annotations
from typing import TYPE_CHECKING
from bs4 import BeautifulSoup

from FunPayAPI.common import enums
from .. import types

if TYPE_CHECKING:
    from FunPayAPI.account import Account


class CategoriesMixin:
    def get_category(self: Account, category_id: int) -> types.Category | None:
        """
        Возвравращает объект категории (игры).

        :param category_id: ID категории (игры).
        :type category_id: :obj:`int`

        :return: объект категории (игры) или :obj:`None`, если категория не была найдена.
        :rtype: :class:`FunPayAPI.types.Category` or :obj:`None`
        """
        return self._sorted_categories.get(category_id)

    @property
    def categories(self: Account) -> list[types.Category]:
        """
        Возвращает все категории (игры) FunPay (парсятся при первом выполнении метода :meth:`FunPayAPI.account.Account.get`).

        :return: все категории (игры) FunPay.
        :rtype: :obj:`list` of :class:`FunPayAPI.types.Category`
        """
        return self._categories

    def get_sorted_categories(self: Account) -> dict[int, types.Category]:
        """
        Возвращает все категории (игры) FunPay в виде словаря {ID: категория}
        (парсятся при первом выполнении метода :meth:`FunPayAPI.account.Account.get`).

        :return: все категории (игры) FunPay в виде словаря {ID: категория}
        :rtype: :obj:`dict` {:obj:`int`: :class:`FunPayAPI.types.Category`}
        """
        return self._sorted_categories

    def get_subcategory(self: Account, subcategory_type: enums.SubCategoryTypes,
                        subcategory_id: int) -> types.SubCategory | None:
        """
        Возвращает объект подкатегории.

        :param subcategory_type: тип подкатегории.
        :type subcategory_type: :class:`FunPayAPI.common.enums.SubCategoryTypes`

        :param subcategory_id: ID подкатегории.
        :type subcategory_id: :obj:`int`

        :return: объект подкатегории или :obj:`None`, если подкатегория не была найдена.
        :rtype: :class:`FunPayAPI.types.SubCategory` or :obj:`None`
        """
        return self._sorted_subcategories[subcategory_type].get(subcategory_id)

    @property
    def subcategories(self: Account) -> list[types.SubCategory]:
        """
        Возвращает все подкатегории FunPay (парсятся при первом выполнении метода Account.get).

        :return: все подкатегории FunPay.
        :rtype: :obj:`list` of :class:`FunPayAPI.types.SubCategory`
        """
        return self._subcategories

    def get_sorted_subcategories(self: Account) -> dict[enums.SubCategoryTypes, dict[int, types.SubCategory]]:
        """
        Возвращает все подкатегории FunPay в виде словаря {тип подкатегории: {ID: подкатегория}}
        (парсятся при первом выполнении метода Account.get).

        :return: все подкатегории FunPay в виде словаря {тип подкатегории: {ID: подкатегория}}
        :rtype: :obj:`dict` {:class:`FunPayAPI.common.enums.SubCategoryTypes`: :obj:`dict` {:obj:`int` :class:`FunPayAPI.types.SubCategory`}}
        """
        return self._sorted_subcategories

    def _setup_categories(self: Account, html: str):
        """
        Парсит категории и подкатегории с основной страницы и добавляет их в свойства класса.

        :param html: HTML страница.
        """
        parser = BeautifulSoup(html, "lxml")
        games_table = parser.find_all("div", {"class": "promo-game-list"})
        if not games_table:
            return

        games_table = games_table[1] if len(games_table) > 1 else games_table[0]
        games_divs = games_table.find_all("div", {"class": "promo-game-item"})
        if not games_divs:
            return
        game_position = 0
        subcategory_position = 0
        for i in games_divs:
            gid = int(i.find("div", {"class": "game-title"}).get("data-id"))
            gname = i.find("a").text
            regional_games = {
                gid: types.Category(gid, gname, position=game_position)
            }
            game_position += 1
            if regional_divs := i.find("div", {"role": "group"}):
                for btn in regional_divs.find_all("button"):
                    regional_game_id = int(btn["data-id"])
                    regional_games[regional_game_id] = types.Category(regional_game_id, f"{gname} ({btn.text})",
                                                                      position=game_position)
                    game_position += 1

            subcategories_divs = i.find_all("ul", {"class": "list-inline"})
            for j in subcategories_divs:
                j_game_id = int(j["data-id"])
                subcategories = j.find_all("li")
                for k in subcategories:
                    a = k.find("a")
                    name, link = a.text, a["href"]
                    stype = types.SubCategoryTypes.CURRENCY if "chips" in link else types.SubCategoryTypes.COMMON
                    sid = int(link.split("/")[-2])
                    sobj = types.SubCategory(sid, name, stype, regional_games[j_game_id], subcategory_position)
                    subcategory_position += 1
                    regional_games[j_game_id].add_subcategory(sobj)
                    self._subcategories.append(sobj)
                    self._sorted_subcategories[stype][sid] = sobj

            for gid in regional_games:
                self._categories.append(regional_games[gid])
                self._sorted_categories[gid] = regional_games[gid]
