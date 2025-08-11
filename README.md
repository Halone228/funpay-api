# FunPayAPI

A modern, asynchronous-first Python wrapper for the FunPay.ru API.

This library provides a flexible and robust way to interact with FunPay, featuring:
- **Asynchronous & Synchronous Clients**: Separate, explicit `AsyncAccount` and `SyncAccount` classes.
- **High Performance**: Built with `primp` for fast HTTP requests.
- **Structured Logging**: Uses `loguru` for clear and informative logging.
- **Clean Architecture**: A mixin-based approach for better separation of concerns.
- **Custom Exceptions**: Specific exceptions for predictable error handling.

---

## Installation

```bash
pip install -U FunPayAPI
```

## Quickstart

### Asynchronous Usage (`AsyncAccount`)

For use in `asyncio` applications. All network-bound methods are coroutines and must be awaited.

```python
import asyncio
from FunPayAPI import AsyncAccount

# It's recommended to store your golden_key in an environment variable
# or another secure method instead of hardcoding it.
GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
    await account.get()

    if account.is_initiated:
        print(f"Successfully logged in as {account.username} (ID: {account.id})")
    else:
        print("Failed to log in.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous Usage (`SyncAccount`)

For use in standard, blocking applications. Methods will block until they complete.

```python
from FunPayAPI import SyncAccount

GOLDEN_KEY = "your_golden_key_here"

account = SyncAccount(golden_key=GOLDEN_KEY)
account.get()

if account.is_initiated:
    print(f"Successfully logged in as {account.username} (ID: {account.id})")
else:
    print("Failed to log in.")
```

## Event Handling with the Updater

The `Runner` allows you to listen for real-time events from FunPay, such as new messages or orders. Use it with `AsyncAccount`.

```python
import asyncio
from FunPayAPI import AsyncAccount, Runner
from FunPayAPI.updater.events import NewMessageEvent

GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
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
from FunPayAPI import AsyncAccount
from FunPayAPI.common.exceptions import FunPayAPIError

GOLDEN_KEY = "invalid_key"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
    try:
        await account.get()
    except FunPayAPIError as e:
        print(f"An API error occurred: {e}")
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
- **Асинхронный и Синхронный Клиенты**: Раздельные, явные классы `AsyncAccount` и `SyncAccount`.
- **Высокая производительность**: Построена на `primp` для быстрых HTTP-запросов.
- **Структурированное логирование**: Использует `loguru` для чистого и информативного логирования.
- **Чистая архитектура**: Mixin-подход для лучшего разделения ответственности.
- **Пользовательские исключения**: Специализированные исключения для предсказуемой обработки ошибок.

---

## Установка

```bash
pip install -U FunPayAPI
```

## Быстрый старт

### Асинхронное использование (`AsyncAccount`)

Для использования в `asyncio` приложениях. Все методы, связанные с сетью, являются корутинами и должны вызываться с `await`.

```python
import asyncio
from FunPayAPI import AsyncAccount

# Рекомендуется хранить ваш golden_key в переменной окружения
# или другом безопасном месте вместо жесткого кодирования.
GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
    await account.get()

    if account.is_initiated:
        print(f"Успешный вход как {account.username} (ID: {account.id})")
    else:
        print("Не удалось войти.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Синхронное использование (`SyncAccount`)

Для использования в стандартных, блокирующих приложениях. Методы будут блокировать выполнение до своего завершения.

```python
from FunPayAPI import SyncAccount

GOLDEN_KEY = "your_golden_key_here"

account = SyncAccount(golden_key=GOLDEN_KEY)
account.get()

if account.is_initiated:
    print(f"Успешный вход как {account.username} (ID: {account.id})")
else:
    print("Не удалось войти.")
```

## Обработка событий с помощью Updater

`Runner` позволяет вам прослушивать события от FunPay в реальном времени, такие как новые сообщения или заказы. Используйте его с `AsyncAccount`.

```python
import asyncio
from FunPayAPI import AsyncAccount, Runner
from FunPayAPI.updater.events import NewMessageEvent

GOLDEN_KEY = "your_golden_key_here"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
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
from FunPayAPI import AsyncAccount
from FunPayAPI.common.exceptions import FunPayAPIError

GOLDEN_KEY = "invalid_key"


async def main():
    account = AsyncAccount(golden_key=GOLDEN_KEY)
    try:
        await account.get()
    except FunPayAPIError as e:
        print(f"Произошла ошибка API: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```
