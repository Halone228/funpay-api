# FunPayAPI

A modern, asynchronous-first Python wrapper for the FunPay.ru API.

This library provides a flexible and robust way to interact with FunPay, featuring:
- **Asynchronous Support**: Built with `asyncio` and `primp` for high-performance, non-blocking operations.
- **Synchronous Mode**: Offers a synchronous client for simpler, blocking use cases.
- **Structured Logging**: Uses `loguru` for clear and informative logging.
- **Clean Architecture**: A mixin-based approach for better separation of concerns.
- **Custom Exceptions**: Specific exceptions for predictable error handling.

---

## Installation

```bash
pip install -U FunPayAPI
```

## Quickstart

### Asynchronous Usage

Here's a simple example of how to initialize the client and fetch your account balance asynchronously.

```python
import asyncio
from FunPayAPI import Account

# It's recommended to store your golden_key in an environment variable
# or another secure method instead of hardcoding it.
GOLDEN_KEY = "your_golden_key_here"


async def main():
    # Initialize the Account in asynchronous mode
    account = Account(golden_key=GOLDEN_KEY, async_=True)

    # Get account data
    await account.get()

    if account.is_initiated:
        print(f"Successfully logged in as {account.username} (ID: {account.id})")
        # To get balance, you need to access a lot page first
        # For example, get your own lots and then get balance from one of them
        # lots = await account.get_my_subcategory_lots(subcategory_id=1)
        # if lots:
        #    balance = await account.get_balance(lots[0].id)
        #    print(f"Balance: {balance.total} {balance.currency}")
    else:
        print("Failed to log in.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous Usage

If you prefer a simpler, blocking approach, you can use the synchronous client.

```python
from FunPayAPI import Account

GOLDEN_KEY = "your_golden_key_here"

# Initialize the Account in synchronous mode (default)
account = Account(golden_key=GOLDEN_KEY)

# Get account data
account.get()

if account.is_initiated:
    print(f"Successfully logged in as {account.username} (ID: {account.id})")
else:
    print("Failed to log in.")
```

## Event Handling with the Updater

The `Updater` allows you to listen for real-time events from FunPay, such as new messages or orders.

```python
import asyncio
from FunPayAPI import Account, Runner
from FunPayAPI.updater.events import NewMessageEvent

GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    await account.get()
    print(f"Logged in as {account.username}")

    runner = Runner(account, async_=True)
    print("Listening for new events...")

    async for event in runner.listen():
        if isinstance(event, NewMessageEvent):
            message = event.message
            print(f"New message from {message.author.username}: {message.text}")
            # Example: reply to a message
            await account.send_message(message.chat_id, "Hello from FunPayAPI!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Updater stopped.")
```

## Error Handling

The library uses a set of custom exceptions that inherit from `FunPayAPIError` for easier error handling.

```python
import asyncio
from FunPayAPI import Account
from FunPayAPI.common.exceptions import RequestFailedError, AccountNotInitiatedError

GOLDEN_KEY = "invalid_key"


async def main():
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    try:
        await account.get()
        # This will raise AccountNotInitiatedError if .get() fails and you try to access attributes
        print(f"Balance: {account.balance.total}")

    except RequestFailedError as e:
        print(f"A request failed: {e}")
    except AccountNotInitiatedError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

---
<br>

# FunPayAPI (Русская документация)

Современная, асинхронная библиотека-обертка для API FunPay.ru.

Эта библиотека предоставляет гибкий и надежный способ взаимодействия с FunPay, включая:
- **Асинхронную поддержку**: Построена на `asyncio` и `primp` для высокопроизводительных, неблокирующих операций.
- **Синхронный режим**: Предлагает синхронный клиент для более простых, блокирующих сценариев.
- **Структурированное логирование**: Использует `loguru` для чистого и информативного логирования.
- **Чистая архитектура**: Mixin-подход для лучшего разделения ответственности.
- **Пользовательские исключения**: Специализированные исключения для предсказуемой обработки ошибок.

---

## Установка

```bash
pip install -U FunPayAPI
```

## Быстрый старт

### Асинхронное использование

Простой пример инициализации клиента и асинхронного получения баланса вашего аккаунта.

```python
import asyncio
from FunPayAPI import Account

# Рекомендуется хранить ваш golden_key в переменной окружения
# или другом безопасном месте вместо жесткого кодирования.
GOLDEN_KEY = "your_golden_key_here"


async def main():
    # Инициализация Account в асинхронном режиме
    account = Account(golden_key=GOLDEN_KEY, async_=True)

    # Получение данных аккаунта
    await account.get()

    if account.is_initiated:
        print(f"Успешный вход как {account.username} (ID: {account.id})")
        # Для получения баланса сначала нужно получить доступ к странице лота
        # Например, получите свои лоты, а затем получите баланс одного из них
        # lots = await account.get_my_subcategory_lots(subcategory_id=1)
        # if lots:
        #    balance = await account.get_balance(lots[0].id)
        #    print(f"Баланс: {balance.total} {balance.currency}")
    else:
        print("Не удалось войти.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Синхронное использование

Если вы предпочитаете более простой, блокирующий подход, вы можете использовать синхронный клиент.

```python
from FunPayAPI import Account

GOLDEN_KEY = "your_golden_key_here"

# Инициализация Account в синхронном режиме (по умолчанию)
account = Account(golden_key=GOLDEN_KEY)

# Получение данных аккаунта
account.get()

if account.is_initiated:
    print(f"Успешный вход как {account.username} (ID: {account.id})")
else:
    print("Не удалось войти.")
```

## Обработка событий с помощью Updater

`Updater` позволяет вам прослушивать события от FunPay в реальном времени, такие как новые сообщения или заказы.

```python
import asyncio
from FunPayAPI import Account, Runner
from FunPayAPI.updater.events import NewMessageEvent

GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    await account.get()
    print(f"Вход как {account.username}")

    runner = Runner(account, async_=True)
    print("Прослушивание новых событий...")

    async for event in runner.listen():
        if isinstance(event, NewMessageEvent):
            message = event.message
            print(f"Новое сообщение от {message.author.username}: {message.text}")
            # Пример: ответ на сообщение
            await account.send_message(message.chat_id, "Привет от FunPayAPI!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Updater остановлен.")
```

## Обработка ошибок

Библиотека использует набор пользовательских исключений, которые наследуются от `FunPayAPIError`, для упрощения обработки ошибок.

```python
import asyncio
from FunPayAPI import Account
from FunPayAPI.common.exceptions import RequestFailedError, AccountNotInitiatedError

GOLDEN_KEY = "invalid_key"


async def main():
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    try:
        await account.get()
        # Это вызовет AccountNotInitiatedError, если .get() не удастся, и вы попытаетесь получить доступ к атрибутам
        print(f"Баланс: {account.balance.total}")

    except RequestFailedError as e:
        print(f"Запрос не удался: {e}")
    except AccountNotInitiatedError as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```
