from __future__ import annotations
from typing import TYPE_CHECKING
from bs4 import BeautifulSoup
from loguru import logger
import json
from . import enums, utils, exceptions
from .. import types
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from ..account import Account


def _update_csrf_token(parser: BeautifulSoup, account: Account):
    try:
        app_data = json.loads(parser.find("body").get("data-app-data"))
        account.csrf_token = app_data.get("csrf-token") or account.csrf_token
    except:
        logger.warning("Произошла ошибка при обновлении csrf.")
        logger.debug("TRACEBACK", exc_info=True)

def parse_account_data(html: str, account: Account) -> None:
    """
    Parses the main page HTML to get account information.
    """
    parser = BeautifulSoup(html, "lxml")
    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()
    account.username = username.text
    app_data = json.loads(parser.find("body").get("data-app-data"))
    account.locale = app_data.get("locale")
    account.id = app_data["userId"]
    account.csrf_token = app_data["csrf-token"]
    account._logout_link = parser.find("a", class_="menu-item-logout").get("href")
    active_sales = parser.find("span", {"class": "badge badge-trade"})
    account.active_sales = int(active_sales.text) if active_sales else 0
    balance = parser.find("span", class_="badge badge-balance")
    if balance:
        balance, currency = balance.text.rsplit(" ", maxsplit=1)
        account.total_balance = int(balance.replace(" ", ""))
        account.currency = utils.parse_currency(currency)
    else:
        account.total_balance = 0
    active_purchases = parser.find("span", {"class": "badge badge-orders"})
    account.active_purchases = int(active_purchases.text) if active_purchases else 0

    if not account.is_initiated:
        _setup_categories(html, account)

def _setup_categories(html: str, account: Account):
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
                account._subcategories.append(sobj)
                account._sorted_subcategories[stype][sid] = sobj

        for gid in regional_games:
            account._categories.append(regional_games[gid])
            account._sorted_categories[gid] = regional_games[gid]

def parse_subcategory_public_lots(html: str, account: Account, subcategory_type: enums.SubCategoryTypes, subcategory_id: int) -> list[types.LotShortcut]:
    parser = BeautifulSoup(html, "lxml")

    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)
    offers = parser.find_all("a", {"class": "tc-item"})
    if not offers:
        return []

    subcategory_obj = account.get_subcategory(subcategory_type, subcategory_id)
    result = []
    sellers = {}
    currency = None
    for offer in offers:
        offer_id = offer["href"].split("id=")[1]
        promo = 'offer-promo' in offer.get('class', [])
        description = offer.find("div", {"class": "tc-desc-text"})
        description = description.text if description else None
        server = offer.find("div", class_="tc-server")
        server = server.text if server else None
        tc_price = offer.find("div", {"class": "tc-price"})
        if subcategory_type is types.SubCategoryTypes.COMMON:
            price = float(tc_price["data-s"])
        else:
            price = float(tc_price.find("div").text.rsplit(maxsplit=1)[0].replace(" ", ""))
        if currency is None:
            currency = utils.parse_currency(tc_price.find("span", class_="unit").text)
            if account.currency != currency:
                account.currency = currency
        seller_soup = offer.find("div", class_="tc-user")
        attributes = {k.replace("data-", "", 1): int(v) if v.isdigit() else v for k, v in offer.attrs.items()
                        if k.startswith("data-")}

        auto = attributes.get("auto") == 1
        tc_amount = offer.find("div", class_="tc-amount")
        amount = tc_amount.text.replace(" ", "") if tc_amount else None
        amount = int(amount) if amount and amount.isdigit() else None
        seller_key = str(seller_soup)
        if seller_key not in sellers:
            online = False
            if attributes.get("online") == 1:
                online = True
            seller_body = offer.find("div", class_="media-body")
            username = seller_body.find("div", class_="media-user-name").text.strip()
            rating_stars = seller_body.find("div", class_="rating-stars")
            if rating_stars is not None:
                rating_stars = len(rating_stars.find_all("i", class_="fas"))
            k_reviews = seller_body.find("div", class_="media-user-reviews")
            if k_reviews:
                k_reviews = "".join([i for i in k_reviews.text if i.isdigit()])
            k_reviews = int(k_reviews) if k_reviews else 0
            user_id = int(seller_body.find("span", class_="pseudo-a")["data-href"].split("/")[-2])
            seller = types.SellerShortcut(user_id, username, online, rating_stars, k_reviews, seller_key)
            sellers[seller_key] = seller
        else:
            seller = sellers[seller_key]
        for i in ("online", "auto"):
            if i in attributes:
                del attributes[i]

        lot_obj = types.LotShortcut(offer_id, server, description, amount, price, currency, subcategory_obj, seller,
                                    auto, promo, attributes, str(offer))
        result.append(lot_obj)
    return result

def parse_my_subcategory_lots(html: str, account: Account, subcategory_id: int) -> list[types.MyLotShortcut]:
    parser = BeautifulSoup(html, "lxml")

    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)
    offers = parser.find_all("a", class_="tc-item")
    if not offers:
        return []

    subcategory_obj = account.get_subcategory(enums.SubCategoryTypes.COMMON, subcategory_id)
    result = []
    currency = None
    for offer in offers:
        offer_id = offer["data-offer"]
        description = offer.find("div", {"class": "tc-desc-text"})
        description = description.text if description else None
        server = offer.find("div", class_="tc-server")
        server = server.text if server else None
        tc_price = offer.find("div", class_="tc-price")
        price = float(tc_price["data-s"])
        if currency is None:
            currency = utils.parse_currency(tc_price.find("span", class_="unit").text)
            if account.currency != currency:
                account.currency = currency
        auto = bool(tc_price.find("i", class_="auto-dlv-icon"))
        tc_amount = offer.find("div", class_="tc-amount")
        amount = tc_amount.text.replace(" ", "") if tc_amount else None
        amount = int(amount) if amount and amount.isdigit() else None
        active = "warning" not in offer.get("class", [])
        lot_obj = types.MyLotShortcut(offer_id, server, description, amount, price, currency, subcategory_obj,
                                        auto, active, str(offer))
        result.append(lot_obj)
    return result

def parse_lot_page(html: str, account: Account, lot_id: int) -> types.LotPage | None:
    parser = BeautifulSoup(html, "lxml")
    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)

    if (page_header := parser.find("h1", class_="page-header")) \
            and page_header.text in ("Предложение не найдено", "Пропозицію не знайдено", "Offer not found"):
        return None

    subcategory_id = int(parser.find("a", class_="js-back-link")['href'].split("/")[-2])
    chat_header = parser.find("div", class_="chat-header")
    if chat_header:
        seller = chat_header.find("div", class_="media-user-name").find("a")
        seller_id = int(seller["href"].split("/")[-2])
        seller_username = seller.text
    else:
        seller_id = account.id
        seller_username = account.username

    short_description = None
    detailed_description = None
    image_urls = []
    for param_item in parser.find_all("div", class_="param-item"):
        if param_name := param_item.find("h5"):
            if param_name.text in ("Краткое описание", "Короткий опис", "Short description"):
                short_description = param_item.find("div").text
            elif param_name.text in ("Подробное описание", "Докладний опис", "Detailed description"):
                detailed_description = param_item.find("div").text
            elif param_name in ("Картинки", "Зображення", "Images"):
                photos = param_item.find_all("a", class_="attachments-thumb")
                if photos:
                    image_urls = [photo.get("href") for photo in photos]

    return types.LotPage(lot_id, account.get_subcategory(enums.SubCategoryTypes.COMMON, subcategory_id),
                            short_description, detailed_description, image_urls, seller_id, seller_username)

def parse_balance(html: str, account: Account) -> types.Balance:
    parser = BeautifulSoup(html, "lxml")

    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)

    balances = parser.find("select", {"name": "method"})
    balance = types.Balance(float(balances["data-balance-total-rub"]), float(balances["data-balance-rub"]),
                            float(balances["data-balance-total-usd"]), float(balances["data-balance-usd"]),
                            float(balances["data-balance-total-eur"]), float(balances["data-balance-eur"]))
    return balance

def parse_chat_history(json_response: dict, account: Account, chat_id: int | str, interlocutor_username: str | None, from_id: int) -> list[types.Message]:
    if not json_response.get("chat") or not json_response["chat"].get("messages"):
        return []
    if json_response["chat"]["node"]["silent"]:
        interlocutor_id = None
    else:
        interlocutors = json_response["chat"]["node"]["name"].split("-")[1:]
        interlocutors.remove(str(account.id))
        interlocutor_id = int(interlocutors[0])

    return _parse_messages(json_response["chat"]["messages"], account, chat_id, interlocutor_id,
                                    interlocutor_username, from_id)

def parse_chats_histories(json_response: dict, account: Account, chats_data: dict[int | str, str | None]) -> dict[int, list[types.Message]]:
    result = {}
    for i in json_response["objects"]:
        if i.get("type") == "c-p-u":
            bv = account.parse_buyer_viewing(i) # This should be moved to parser
            account.runner.buyers_viewing[bv.buyer_id] = bv
        elif i.get("type") == "chat_node":
            if not i.get("data"):
                result[i.get("id")] = []
                continue
            if i["data"]["node"]["silent"]:
                interlocutor_id = None
                interlocutor_name = None
            else:
                interlocutors = i["data"]["node"]["name"].split("-")[1:]
                interlocutors.remove(str(account.id))
                interlocutor_id = int(interlocutors[0])
                interlocutor_name = chats_data[i.get("id")]
            messages = _parse_messages(i["data"]["messages"], account, i.get("id"), interlocutor_id, interlocutor_name)
            result[i.get("id")] = messages
    return result

def _parse_messages(json_messages: dict, account: Account, chat_id: int | str,
                    interlocutor_id: int | None = None, interlocutor_username: str | None = None,
                    from_id: int = 0) -> list[types.Message]:
    messages = []
    ids = {account.id: account.username, 0: "FunPay"}
    badges = {}
    if interlocutor_id is not None:
        ids[interlocutor_id] = interlocutor_username

    for i in json_messages:
        if i["id"] < from_id:
            continue
        author_id = i["author"]
        parser = BeautifulSoup(i["html"].replace("<br>", "\n"), "lxml")

        # Если ник или бейдж написавшего неизвестен, но есть блок с данными об авторе сообщения
        if None in [ids.get(author_id), badges.get(author_id)] and (
                author_div := parser.find("div", {"class": "media-user-name"})):
            if badges.get(author_id) is None:
                badge = author_div.find("span", {"class": "chat-msg-author-label label label-success"})
                badges[author_id] = badge.text if badge else 0
            if ids.get(author_id) is None:
                author = author_div.find("a").text.strip()
                ids[author_id] = author
                if account.chat_id_private(chat_id) and author_id == interlocutor_id and not interlocutor_username:
                    interlocutor_username = author
                    ids[interlocutor_id] = interlocutor_username
        by_bot = False
        by_vertex = False
        image_name = None
        if account.chat_id_private(chat_id) and (image_tag := parser.find("a", {"class": "chat-img-link"})):
            image_name = image_tag.find("img")
            image_name = image_name.get('alt') if image_name else None
            image_link = image_tag.get("href")
            message_text = None
            # "Отправлено_с_помощью_бота_FunPay_Cardinal.png", "funpay_cardinal_image.png"
            if isinstance(image_name, str) and "funpay_cardinal" in image_name.lower():
                by_bot = True
            elif image_name == "funpay_vertex_image.png":
                by_vertex = True

        else:
            image_link = None
            if author_id == 0:
                message_text = parser.find("div", role="alert").text.strip()
            else:
                message_text = parser.find("div", {"class": "chat-msg-text"}).text

            if message_text.startswith(account.bot_character) or \
                    message_text.startswith(account.old_bot_character) and author_id == account.id:
                message_text = message_text[1:]
                by_bot = True
            # todo придумать, как отсеять юзеров со старыми версиями кардинала (подождать обнову фп?)
            # elif message_text.startswith(self.__old_bot_character):
            #     by_vertex = True

        message_obj = types.Message(i["id"], message_text, chat_id, interlocutor_username, interlocutor_id,
                                    None, author_id, i["html"], image_link, image_name, determine_msg_type=False)
        message_obj.by_bot = by_bot
        message_obj.by_vertex = by_vertex
        message_obj.type = types.MessageTypes.NON_SYSTEM if author_id != 0 else message_obj.get_message_type()

        messages.append(message_obj)

    for i in messages:
        i.author = ids.get(i.author_id)
        i.chat_name = interlocutor_username
        i.badge = badges.get(i.author_id) if badges.get(i.author_id) != 0 else None
        parser = BeautifulSoup(i.html, "lxml")
        if i.badge:
            i.is_employee = True
            if i.badge in ("поддержка", "підтримка", "support"):
                i.is_support = True
            elif i.badge in ("модерация", "модерація", "moderation"):
                i.is_moderation = True
            elif i.badge in ("арбитраж", "арбітраж", "arbitration"):
                i.is_arbitration = True
        default_label = parser.find("div", {"class": "media-user-name"})
        default_label = default_label.find("span", {
            "class": "chat-msg-author-label label label-default"}) if default_label else None
        if default_label:
            if default_label.text in ("автовідповідь", "автоответ", "auto-reply"):
                i.is_autoreply = True
        i.badge = default_label.text if (i.badge is None and default_label is not None) else i.badge
        if i.type != types.MessageTypes.NON_SYSTEM:
            users = parser.find_all('a', href=lambda href: href and '/users/' in href)
            if users:
                i.initiator_username = users[0].text
                i.initiator_id = int(users[0]["href"].split("/")[-2])
                if i.type in (types.MessageTypes.ORDER_PURCHASED, types.MessageTypes.ORDER_CONFIRMED,
                                types.MessageTypes.NEW_FEEDBACK,
                                types.MessageTypes.FEEDBACK_CHANGED,
                                types.MessageTypes.FEEDBACK_DELETED):
                    if i.initiator_id == account.id:
                        i.i_am_seller = False
                        i.i_am_buyer = True
                    else:
                        i.i_am_seller = True
                        i.i_am_buyer = False
                elif i.type in (types.MessageTypes.NEW_FEEDBACK_ANSWER, types.MessageTypes.FEEDBACK_ANSWER_CHANGED,
                                types.MessageTypes.FEEDBACK_ANSWER_DELETED, types.MessageTypes.REFUND):
                    if i.initiator_id == account.id:
                        i.i_am_seller = True
                        i.i_am_buyer = False
                    else:
                        i.i_am_seller = False
                        i.i_am_buyer = True
                elif len(users) > 1:
                    last_user_id = int(users[-1]["href"].split("/")[-2])
                    if i.type == types.MessageTypes.ORDER_CONFIRMED_BY_ADMIN:
                        if last_user_id == account.id:
                            i.i_am_seller = True
                            i.i_am_buyer = False
                        else:
                            i.i_am_seller = False
                            i.i_am_buyer = True
                    elif i.type == types.MessageTypes.REFUND_BY_ADMIN:
                        if last_user_id == account.id:
                            i.i_am_seller = False
                            i.i_am_buyer = True
                        else:
                            i.i_am_seller = True
                            i.i_am_buyer = False

    return messages

def parse_user_profile(html: str, account: Account, user_id: int) -> types.UserProfile:
    parser = BeautifulSoup(html, "lxml")

    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)

    username = parser.find("span", {"class": "mr4"}).text
    user_status = parser.find("span", {"class": "media-user-status"})
    user_status = user_status.text if user_status else ""
    avatar_link = parser.find("div", {"class": "avatar-photo"}).get("style").split("(")[1].split(")")[0]
    avatar_link = avatar_link if avatar_link.startswith("https") else f"https://funpay.com{avatar_link}"
    banned = bool(parser.find("span", {"class": "label label-danger"}))
    user_obj = types.UserProfile(user_id, username, avatar_link, "Онлайн" in user_status or "Online" in user_status,
                                    banned, html)

    subcategories_divs = parser.find_all("div", {"class": "offer-list-title-container"})

    if not subcategories_divs:
        return user_obj

    for i in subcategories_divs:
        subcategory_link = i.find("h3").find("a").get("href")
        subcategory_id = int(subcategory_link.split("/")[-2])
        subcategory_type = types.SubCategoryTypes.CURRENCY if "chips" in subcategory_link else \
            types.SubCategoryTypes.COMMON
        subcategory_obj = account.get_subcategory(subcategory_type, subcategory_id)
        if not subcategory_obj:
            continue

        offers = i.parent.find_all("a", {"class": "tc-item"})
        currency = None
        for j in offers:
            offer_id = j["href"].split("id=")[1]
            description = j.find("div", {"class": "tc-desc-text"})
            description = description.text if description else None
            server = j.find("div", class_="tc-server")
            server = server.text if server else None
            auto = j.find("i", class_="auto-dlv-icon") is not None
            tc_price = j.find("div", {"class": "tc-price"})
            tc_amount = j.find("div", class_="tc-amount")
            amount = tc_amount.text.replace(" ", "") if tc_amount else None
            amount = int(amount) if amount and amount.isdigit() else None
            if subcategory_obj.type is types.SubCategoryTypes.COMMON:
                price = float(tc_price["data-s"])
            else:
                price = float(tc_price.find("div").text.rsplit(maxsplit=1)[0].replace(" ", ""))
            if currency is None:
                currency = utils.parse_currency(tc_price.find("span", class_="unit").text)
                if account.currency != currency:
                    account.currency = currency
            lot_obj = types.LotShortcut(offer_id, server, description, amount, price, currency, subcategory_obj,
                                        None, auto,
                                        None, None, str(j))
            user_obj.add_lot(lot_obj)
    return user_obj

def parse_chat(html: str, account: Account, chat_id: int, with_history: bool) -> types.Chat:
    parser = BeautifulSoup(html, "lxml")
    if (name := parser.find("div", {"class": "chat-header"}).find("div", {"class": "media-user-name"}).find(
            "a").text) in ("Чат", "Chat"):
        raise Exception("chat not found")  # todo

    _update_csrf_token(parser, account)

    if not (chat_panel := parser.find("div", {"class": "param-item chat-panel"})):
        text, link = None, None
    else:
        a = chat_panel.find("a")
        text, link = a.text, a["href"]
    if with_history:
        history = account.get_chat_history(chat_id, interlocutor_username=name)
    else:
        history = []
    return types.Chat(chat_id, name, link, text, html, history)

def parse_order(html: str, account: Account, order_id: str) -> types.Order:
    parser = BeautifulSoup(html, "lxml")
    username = parser.find("div", {"class": "user-link-name"})
    if not username:
        raise exceptions.UnauthorizedError()

    _update_csrf_token(parser, account)

    if (span := parser.find("span", {"class": "text-warning"})) and span.text in (
            "Возврат", "Повернення", "Refund"):
        status = types.OrderStatuses.REFUNDED
    elif (span := parser.find("span", {"class": "text-success"})) and span.text in ("Закрыт", "Закрито", "Closed"):
        status = types.OrderStatuses.CLOSED
    else:
        status = types.OrderStatuses.PAID

    short_description = None
    full_description = None
    sum_ = None
    currency = enums.Currency.UNKNOWN
    subcategory = None
    order_secrets = []
    stop_params = False
    lot_params = []
    buyer_params = {}

    amount = 1
    for div in parser.find_all("div", {"class": "param-item"}):
        if not (h := div.find("h5")):
            continue
        if not stop_params and div.find_previous("hr"):
            stop_params = True

        if h.text in ("Краткое описание", "Короткий опис", "Short description"):
            stop_params = True
            short_description = div.find("div").text
        elif h.text in ("Подробное описание", "Докладний опис", "Detailed description"):
            stop_params = True
            full_description = div.find("div").text
        elif h.text in ("Сумма", "Сума", "Total"):
            sum_ = float(div.find("span").text.replace(" ", ""))
            currency = utils.parse_currency(div.find("strong").text)
        elif h.text in ("Категория", "Категорія", "Category",
                        "Валюта", "Currency"):
            subcategory_link = div.find("a").get("href")
            subcategory_split = subcategory_link.split("/")
            subcategory_id = int(subcategory_split[-2])
            subcategory_type = types.SubCategoryTypes.COMMON if "lots" in subcategory_link else \
                types.SubCategoryTypes.CURRENCY
            subcategory = account.get_subcategory(subcategory_type, subcategory_id)
        elif h.text in ("Оплаченный товар", "Оплаченные товары",
                        "Оплачений товар", "Оплачені товари",
                        "Paid product", "Paid products"):
            secret_placeholders = div.find_all("span", class_="secret-placeholder")
            order_secrets = [i.text for i in secret_placeholders]
        elif h.text in ("Количество", "Amount", "Кількість"):
            div2 = div.find("div", class_="text-bold")
            if div2:
                match = utils.RegularExpressions().PRODUCTS_AMOUNT_ORDER.fullmatch(div2.text)
                if match:
                    amount = int(match.group(1).replace(" ", ""))
        elif h.text in ("Відкрито", "Открыт", "Open"):
            continue  # todo
        elif h.text in ("Закрито", "Закрыт", "Closed"):
            continue  # todo
        elif not stop_params and h.text not in ("Игра", "Гра", "Game"):
            div2 = div.find("div")
            if div2:
                res = div2.text.strip()
                lot_params.append((h.text, res))
        elif stop_params:
            div2 = div.find("div", class_="text-bold")
            if div2:
                buyer_params[h.text] = div2.text
    if not stop_params:
        lot_params = []

    chat = parser.find("div", {"class": "chat-header"})
    chat_link = chat.find("div", {"class": "media-user-name"}).find("a")
    interlocutor_name = chat_link.text
    interlocutor_id = int(chat_link.get("href").split("/")[-2])
    nav_bar = parser.find("ul", {"class": "nav navbar-nav navbar-right logged"})
    active_item = nav_bar.find("li", {"class": "active"})
    if any(i in active_item.find("a").text.strip() for i in ("Продажи", "Продажі", "Sales")):
        buyer_id, buyer_username = interlocutor_id, interlocutor_name
        seller_id, seller_username = account.id, account.username
    else:
        buyer_id, buyer_username = account.id, account.username
        seller_id, seller_username = interlocutor_id, interlocutor_name
    id1, id2 = sorted([buyer_id, seller_id])
    chat_id = f"users-{id1}-{id2}"
    review_obj = parser.find("div", {"class": "order-review"})
    if not (stars_obj := review_obj.find("div", {"class": "rating"})):
        stars, text = None, None
    else:
        stars = int(stars_obj.find("div").get("class")[0].split("rating")[1])
        text = review_obj.find("div", {"class": "review-item-text"}).text.strip()
    hidden = review_obj.find("span", class_="text-warning") is not None
    if not (reply_obj := review_obj.find("div", {"class": "review-item-answer review-compiled-reply"})):
        reply = None
    else:
        reply = reply_obj.find("div").text.strip()

    if all([not text, not reply]):
        review = None
    else:
        review = types.Review(stars, text, reply, False, str(review_obj), hidden, order_id, buyer_username,
                                buyer_id, bool(text and text.endswith(account.bot_character)),
                                bool(reply and reply.endswith(account.bot_character)))
    order = types.Order(order_id, status, subcategory, lot_params, buyer_params,
                        short_description, full_description, amount,
                        sum_, currency, buyer_id, buyer_username, seller_id, seller_username, chat_id,
                        html, review, order_secrets)
    return order

def parse_sales(html: str, account: Account, include_paid: bool, include_closed: bool, include_refunded: bool, exclude_ids: list[str] | None = None, start_from: str | None = None) -> \
            tuple[str | None, list[types.OrderShortcut], str, dict[str, types.SubCategory]]:
    parser = BeautifulSoup(html, "lxml")

    if not start_from:
        username = parser.find("div", {"class": "user-link-name"})
        if not username:
            raise exceptions.UnauthorizedError()

    next_order_id = parser.find("input", {"type": "hidden", "name": "continue"})
    next_order_id = next_order_id.get("value") if next_order_id else None

    order_divs = parser.find_all("a", {"class": "tc-item"})
    subcategories = {}
    if not start_from:
        app_data = json.loads(parser.find("body").get("data-app-data"))
        locale = app_data.get("locale")
        account.csrf_token = app_data.get("csrf-token") or account.csrf_token
        games_options = parser.find("select", attrs={"name": "game"})
        if games_options:
            games_options = games_options.find_all(lambda x: x.name == "option" and x.get("value"))
            for game_option in games_options:
                game_name = game_option.text
                sections_list = json.loads(game_option.get("data-data"))
                for key, section_name in sections_list:
                    section_type, section_id = key.split("-")
                    section_type = types.SubCategoryTypes.COMMON if section_type == "lot" else types.SubCategoryTypes.CURRENCY
                    section_id = int(section_id)
                    subcategories[f"{game_name}, {section_name}"] = account.get_subcategory(section_type, section_id)
    else:
        locale = None

    if not order_divs:
        return None, [], locale, subcategories

    sales = []
    for div in order_divs:
        classname = div.get("class")
        if "warning" in classname:
            if not include_refunded:
                continue
            order_status = types.OrderStatuses.REFUNDED
        elif "info" in classname:
            if not include_paid:
                continue
            order_status = types.OrderStatuses.PAID
        else:
            if not include_closed:
                continue
            order_status = types.OrderStatuses.CLOSED

        order_id = div.find("div", {"class": "tc-order"}).text[1:]
        if exclude_ids and order_id in exclude_ids:
            continue

        description = div.find("div", {"class": "order-desc"}).find("div").text
        tc_price = div.find("div", {"class": "tc-price"}).text
        price, currency = tc_price.rsplit(maxsplit=1)
        price = float(price.replace(" ", ""))
        currency = utils.parse_currency(currency)

        buyer_div = div.find("div", {"class": "media-user-name"}).find("span")
        buyer_username = buyer_div.text
        buyer_id = int(buyer_div.get("data-href")[:-1].split("/users/")[1])
        subcategory_name = div.find("div", {"class": "text-muted"}).text
        subcategory = None
        if subcategories:
            subcategory = subcategories.get(subcategory_name)

        now = datetime.now()
        order_date_text = div.find("div", {"class": "tc-date-time"}).text
        if any(today in order_date_text for today in ("сегодня", "сьогодні", "today")):  # сегодня, ЧЧ:ММ
            h, m = order_date_text.split(", ")[1].split(":")
            order_date = datetime(now.year, now.month, now.day, int(h), int(m))
        elif any(yesterday in order_date_text for yesterday in ("вчера", "вчора", "yesterday")):  # вчера, ЧЧ:ММ
            h, m = order_date_text.split(", ")[1].split(":")
            temp = now - timedelta(days=1)
            order_date = datetime(temp.year, temp.month, temp.day, int(h), int(m))
        elif order_date_text.count(" ") == 2:  # ДД месяца, ЧЧ:ММ
            split = order_date_text.split(", ")
            day, month = split[0].split()
            day, month = int(day), utils.MONTHS[month]
            h, m = split[1].split(":")
            order_date = datetime(now.year, month, day, int(h), int(m))
        else:  # ДД месяца ГГГГ, ЧЧ:ММ
            split = order_date_text.split(", ")
            day, month, year = split[0].split()
            day, month, year = int(day), utils.MONTHS[month], int(year)
            h, m = split[1].split(":")
            order_date = datetime(year, month, day, int(h), int(m))
        id1, id2 = sorted([buyer_id, account.id])
        chat_id = f"users-{id1}-{id2}"
        order_obj = types.OrderShortcut(order_id, description, price, currency, buyer_username, buyer_id, chat_id,
                                        order_status, order_date, subcategory_name, subcategory, str(div))
        sales.append(order_obj)

    return next_order_id, sales, locale, subcategories

def parse_chats(html: str, account: Account) -> list[types.ChatShortcut]:
    parser = BeautifulSoup(html, "lxml")
    chats = parser.find_all("a", {"class": "contact-item"})
    chats_objs = []

    for msg in chats:
        chat_id = int(msg["data-id"])
        last_msg_text = msg.find("div", {"class": "contact-item-message"}).text
        unread = True if "unread" in msg.get("class") else False
        chat_with = msg.find("div", {"class": "media-user-name"}).text
        node_msg_id = int(msg.get('data-node-msg'))
        user_msg_id = int(msg.get('data-user-msg'))
        by_bot = False
        by_vertex = False
        is_image = last_msg_text in ("Изображение", "Зображення", "Image")
        if last_msg_text.startswith(account.bot_character):
            last_msg_text = last_msg_text[1:]
            by_bot = True
        elif last_msg_text.startswith(account.old_bot_character):
            last_msg_text = last_msg_text[1:]
            by_vertex = True
        chat_obj = types.ChatShortcut(chat_id, chat_with, last_msg_text, node_msg_id, user_msg_id, unread, str(msg))
        if not is_image:
            chat_obj.last_by_bot = by_bot
            chat_obj.last_by_vertex = by_vertex

        chats_objs.append(chat_obj)
    return chats_objs
