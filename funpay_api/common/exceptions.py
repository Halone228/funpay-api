from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from primp.response import Response


class funpay_apiError(Exception):
    """Base class for all funpay_api exceptions."""
    pass


class AccountNotInitiatedError(funpay_apiError):
    """Raised when the account has not been initiated with .get() before calling a method."""
    def __init__(self):
        super().__init__("The account has not been initiated with .get() before calling this method.")


class RequestFailedError(funpay_apiError):
    """Raised when a request to FunPay fails."""
    def __init__(self, response: Response):
        self.response = response
        super().__init__(f"Request to FunPay failed with status code {response.status_code}.")


class ImageUploadError(funpay_apiError):
    """Raised when an image upload fails."""
    def __init__(self, response: Response, message: str | None):
        self.response = response
        self.message = message
        super().__init__(f"Image upload failed. Message: {message}")


class MessageNotDeliveredError(funpay_apiError):
    """Raised when a message is not delivered."""
    def __init__(self, response: Response, message: str | None, chat_id: int | str):
        self.response = response
        self.message = message
        self.chat_id = chat_id
        super().__init__(f"Message to chat {chat_id} not delivered. Reason: {message}")


class FeedbackEditingError(funpay_apiError):
    """Raised when there is an error editing feedback."""
    def __init__(self, response: Response, message: str | None, order_id: str):
        self.response = response
        self.message = message
        self.order_id = order_id
        super().__init__(f"Error editing feedback for order {order_id}. Reason: {message}")


class RefundError(funpay_apiError):
    """Raised when a refund fails."""
    def __init__(self, response: Response, message: str | None, order_id: str):
        self.response = response
        self.message = message
        self.order_id = order_id
        super().__init__(f"Refund for order {order_id} failed. Reason: {message}")


class WithdrawError(funpay_apiError):
    """Raised when a withdrawal fails."""
    def __init__(self, response: Response, message: str | None):
        self.response = response
        self.message = message
        super().__init__(f"Withdrawal failed. Reason: {message}")


class RaiseError(funpay_apiError):
    """Raised when raising lots fails."""
    def __init__(self, response: Response, category_name: str, message: str | None, wait_time: int | None):
        self.response = response
        self.category_name = category_name
        self.message = message
        self.wait_time = wait_time
        super().__init__(f"Failed to raise lots for category {category_name}. Reason: {message}")


class LotParsingError(funpay_apiError):
    """Raised when parsing a lot fails."""
    def __init__(self, response: Response, message: str | None, lot_id: int):
        self.response = response
        self.message = message
        self.lot_id = lot_id
        super().__init__(f"Failed to parse lot {lot_id}. Reason: {message}")


class LotSavingError(funpay_apiError):
    """Raised when saving a lot fails."""
    def __init__(self, response: Response, message: str | None, lot_id: int, errors: dict[str, str]):
        self.response = response
        self.message = message
        self.lot_id = lot_id
        self.errors = errors
        super().__init__(f"Failed to save lot {lot_id}. Reason: {message}, Errors: {errors}")
