import asyncio
from FunPayAPI import Account, Runner
from FunPayAPI.updater.events import NewMessageEvent
from FunPayAPI.common.exceptions import FunPayAPIError, AccountNotInitiatedError

# NOTE: This is a dummy key and is expected to fail authentication.
# The purpose of this test is to verify that the code runs without syntax/import errors
# and raises the correct custom exceptions.
GOLDEN_KEY = "your_golden_key_here"


async def test_async_usage():
    print("--- Testing Asynchronous Usage ---")
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    try:
        await account.get()
        if account.is_initiated:
            print("Login successful (this should not happen with a dummy key).")
        else:
            # This path is unlikely to be hit due to exception, but good to have.
            print("Failed to log in (as expected).")
    except FunPayAPIError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during async usage test: {e}")
    print("--- Asynchronous Usage Test Complete ---\n")


async def test_sync_emulation():
    print("--- Testing Synchronous-Style Usage ---")
    # This test emulates how a user in a sync context would run a single async command.
    account = Account(golden_key=GOLDEN_KEY, async_=True)
    try:
        # The user would wrap the single async call in asyncio.run()
        await account.get()
        if account.is_initiated:
            print("Login successful (this should not happen with a dummy key).")
    except FunPayAPIError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during sync emulation test: {e}")
    print("--- Synchronous-Style Usage Test Complete ---\n")


async def test_error_handling():
    print("--- Testing Error Handling ---")
    account = Account(golden_key="invalid_key", async_=True)
    try:
        await account.get()
    except FunPayAPIError as e:
        print(f"Successfully caught expected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during error handling test: {e}")
    print("--- Error Handling Test Complete ---\n")


async def main():
    await test_async_usage()
    await test_sync_emulation()
    await test_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
