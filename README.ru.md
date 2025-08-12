# funpay_api(Русская документация)

Современная, асинхронная библиотека-обертка для API FunPay.ru.

Эта библиотека предоставляет гибкий и надежный способ взаимодействия с FunPay, включая:
- **Асинхронный и Синхронный Клиенты**: Раздельные, явные классы `AsyncAccount` и `SyncAccount`.
- **Высокая производительность**: Построена на `primp` для быстрых HTTP-запросов.
- **Структурированное логирование**: Использует `loguru` для чистого и информативного логирования.
- **Чистая архитектура**: Mixin-подход для лучшего разделения ответственности.
- **Пользовательские исключения**: Специализированные исключения для предсказуемой обработки ошибок.

---

## Установка

Временно недоступно

```bash
pip install -U funpay-api
```

## Быстрый старт

### Асинхронное использование (`AsyncAccount`)

Для использования в `asyncio` приложениях. Все методы, связанные с сетью, являются корутинами и должны вызываться с `await`.

```python
import asyncio
from funpay_api import AsyncAccount

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
from funpay_api import SyncAccount

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
from funpay_api import AsyncAccount, Runner
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
from funpay_api import AsyncAccount
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
