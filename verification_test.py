import asyncio
from funpay_api import AsyncAccount, SyncAccount
from funpay_api.common.exceptions import funpay_apiError

# NOTE: This is a dummy key and is expected to fail authentication.
# The purpose of this test is to verify that the code runs without syntax/import errors
# and raises the correct custom exceptions for both clients.
GOLDEN_KEY = "your_golden_key_here"


async def test_async_client():
    print("--- Testing AsyncAccount ---")
    account = AsyncAccount(golden_key=GOLDEN_KEY)
    try:
        await account.get()
        if account.is_initiated:
            print("Login successful with AsyncAccount (this should not happen with a dummy key).")
    except funpay_apiError as e:
        print(f"AsyncAccount caught expected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during AsyncAccount test: {e}")
    print("--- AsyncAccount Test Complete ---\n")


def test_sync_client():
    print("--- Testing SyncAccount ---")
    account = SyncAccount(golden_key=GOLDEN_KEY)
    try:
        account.get()
        if account.is_initiated:
            print("Login successful with SyncAccount (this should not happen with a dummy key).")
    except funpay_apiError as e:
        print(f"SyncAccount caught expected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during SyncAccount test: {e}")
    print("--- SyncAccount Test Complete ---\n")


async def main():
    await test_async_client()
    # Run the synchronous test in a separate thread to avoid event loop conflicts
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, test_sync_client)


if __name__ == "__main__":
    asyncio.run(main())
