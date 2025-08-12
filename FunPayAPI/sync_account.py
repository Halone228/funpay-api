import asyncio
from typing import Literal, Optional, List, Dict, Tuple, IO

from .async_account import AsyncAccount
from . import types

class SyncAccount:
    """
    Предоставляет синхронный интерфейс для взаимодействия с FunPay.
    Является оболочкой над :class:`AsyncAccount`, запуская асинхронные методы в новом event loop.
    """
    def __init__(self, golden_key: str, user_agent: str | None = None,
                 requests_timeout: int | float = 10, proxy: Optional[dict] = None,
                 locale: Literal["ru", "en", "uk"] | None = None):

        # SyncAccount содержит экземпляр AsyncAccount и делегирует ему вызовы.
        self._async_account = AsyncAccount(golden_key, user_agent, requests_timeout, proxy, locale)

    def __getattr__(self, name):
        # Делегируем доступ к атрибутам (напр. self.id, self.username)
        return getattr(self._async_account, name)

    def _run_async(self, coro):
        # Вспомогательный метод для синхронного запуска корутин.
        return asyncio.run(coro)

    # Обертки для всех публичных асинхронных методов
    def get(self, update_phpsessid: bool = True) -> "SyncAccount":
        self._run_async(self._async_account.get(update_phpsessid=update_phpsessid))
        return self

    def get_subcategory_public_lots(self, *args, **kwargs) -> List[types.LotShortcut]:
        return self._run_async(self._async_account.get_subcategory_public_lots(*args, **kwargs))

    def get_my_subcategory_lots(self, *args, **kwargs) -> List[types.MyLotShortcut]:
        return self._run_async(self._async_account.get_my_subcategory_lots(*args, **kwargs))

    def get_lot_page(self, *args, **kwargs):
        return self._run_async(self._async_account.get_lot_page(*args, **kwargs))

    def get_lot_fields(self, *args, **kwargs) -> types.LotFields:
        return self._run_async(self._async_account.get_lot_fields(*args, **kwargs))

    def get_chip_fields(self, *args, **kwargs) -> types.ChipFields:
        return self._run_async(self._async_account.get_chip_fields(*args, **kwargs))

    def save_offer(self, *args, **kwargs):
        return self._run_async(self._async_account.save_offer(*args, **kwargs))

    def save_chip(self, *args, **kwargs):
        return self._run_async(self._async_account.save_chip(*args, **kwargs))

    def save_lot(self, *args, **kwargs):
        return self._run_async(self._async_account.save_lot(*args, **kwargs))

    def delete_lot(self, *args, **kwargs):
        return self._run_async(self._async_account.delete_lot(*args, **kwargs))

    def get_raise_modal(self, *args, **kwargs) -> dict:
        return self._run_async(self._async_account.get_raise_modal(*args, **kwargs))

    def raise_lots(self, *args, **kwargs) -> bool:
        return self._run_async(self._async_account.raise_lots(*args, **kwargs))

    def get_chat_history(self, *args, **kwargs) -> List[types.Message]:
        return self._run_async(self._async_account.get_chat_history(*args, **kwargs))

    def get_chats_histories(self, *args, **kwargs) -> Dict[int, List[types.Message]]:
        return self._run_async(self._async_account.get_chats_histories(*args, **kwargs))

    def upload_image(self, *args, **kwargs) -> int:
        return self._run_async(self._async_account.upload_image(*args, **kwargs))

    def send_message(self, *args, **kwargs) -> types.Message:
        return self._run_async(self._async_account.send_message(*args, **kwargs))

    def send_image(self, *args, **kwargs) -> types.Message:
        return self._run_async(self._async_account.send_image(*args, **kwargs))

    def request_chats(self, *args, **kwargs) -> List[types.ChatShortcut]:
        return self._run_async(self._async_account.request_chats(*args, **kwargs))

    def get_chats(self, *args, **kwargs) -> Dict[int, types.ChatShortcut]:
        return self._run_async(self._async_account.get_chats(*args, **kwargs))

    def get_chat_by_name(self, *args, **kwargs) -> Optional[types.ChatShortcut]:
        return self._run_async(self._async_account.get_chat_by_name(*args, **kwargs))

    def get_chat_by_id(self, *args, **kwargs) -> Optional[types.ChatShortcut]:
        return self._run_async(self._async_account.get_chat_by_id(*args, **kwargs))

    def get_chat(self, *args, **kwargs) -> types.Chat:
        return self._run_async(self._async_account.get_chat(*args, **kwargs))

    def send_review(self, *args, **kwargs) -> str:
        return self._run_async(self._async_account.send_review(*args, **kwargs))

    def delete_review(self, *args, **kwargs) -> str:
        return self._run_async(self._async_account.delete_review(*args, **kwargs))

    def refund(self, *args, **kwargs):
        return self._run_async(self._async_account.refund(*args, **kwargs))

    def get_order_shortcut(self, *args, **kwargs) -> types.OrderShortcut:
        return self._run_async(self._async_account.get_order_shortcut(*args, **kwargs))

    def get_order(self, *args, **kwargs) -> types.Order:
        return self._run_async(self._async_account.get_order(*args, **kwargs))

    def get_sales(self, *args, **kwargs) -> Tuple[Optional[str], List[types.OrderShortcut], str, Dict[str, types.SubCategory]]:
        return self._run_async(self._async_account.get_sales(*args, **kwargs))

    def get_sells(self, *args, **kwargs) -> Tuple[Optional[str], List[types.OrderShortcut]]:
        return self._run_async(self._async_account.get_sells(*args, **kwargs))

    def withdraw(self, *args, **kwargs) -> float:
        return self._run_async(self._async_account.withdraw(*args, **kwargs))

    def get_balance(self, *args, **kwargs) -> types.Balance:
        return self._run_async(self._async_account.get_balance(*args, **kwargs))

    def calc(self, *args, **kwargs):
        return self._run_async(self._async_account.calc(*args, **kwargs))

    def get_exchange_rate(self, *args, **kwargs) -> Tuple[float, types.Currency]:
        return self._run_async(self._async_account.get_exchange_rate(*args, **kwargs))

    def logout(self, *args, **kwargs) -> None:
        return self._run_async(self._async_account.logout(*args, **kwargs))

    def get_user(self, *args, **kwargs) -> types.UserProfile:
        return self._run_async(self._async_account.get_user(*args, **kwargs))
