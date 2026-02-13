import pytest
import contextvars
import asyncio

from api_key_context import set_api_key, get_api_key, clear_api_key


class TestApiKeyContext:
    """Unit tests for API key context variable management."""

    def test_set_api_key_stores_value(self):
        """Test set_api_key stores API key in context."""
        # Clear any existing context
        clear_api_key()

        api_key = "test-api-key-12345"
        token = set_api_key(api_key)

        # Verify the API key is stored
        assert get_api_key() == api_key
        assert token is not None
        assert isinstance(token, contextvars.Token)

    def test_get_api_key_returns_none_initially(self):
        """Test get_api_key returns None when not set."""
        # Clear any existing context
        clear_api_key()

        # Should return None when not set
        assert get_api_key() is None

    def test_clear_api_key_with_token_resets_to_previous_value(self):
        """Test clear_api_key with token resets to previous value."""
        # Start with first API key
        clear_api_key()
        first_key = "first-api-key"
        token1 = set_api_key(first_key)
        assert get_api_key() == first_key

        # Set second API key
        second_key = "second-api-key"
        token2 = set_api_key(second_key)
        assert get_api_key() == second_key

        # Clear with token2 should restore to first_key
        clear_api_key(token2)
        assert get_api_key() == first_key

        # Clear with token1 should reset to None
        clear_api_key(token1)
        assert get_api_key() is None

    def test_clear_api_key_without_token_sets_to_none(self):
        """Test clear_api_key without token sets context to None."""
        # Set an API key
        api_key = "test-api-key"
        set_api_key(api_key)
        assert get_api_key() == api_key

        # Clear without token
        clear_api_key()

        # Should be None
        assert get_api_key() is None

    def test_set_api_key_with_none(self):
        """Test set_api_key can store None explicitly."""
        # Set initial value
        set_api_key("test-key")

        # Set to None
        token = set_api_key(None)
        assert get_api_key() is None
        assert token is not None

    @pytest.mark.asyncio
    async def test_context_isolation_between_async_tasks(self):
        """Test that context is isolated between async tasks."""
        results = {}

        async def task_1():
            # Set API key for task 1
            set_api_key("task-1-key")
            await asyncio.sleep(0.01)  # Yield to allow task 2 to run
            results["task_1"] = get_api_key()

        async def task_2():
            # Set API key for task 2
            set_api_key("task-2-key")
            await asyncio.sleep(0.01)  # Yield to allow task 1 to continue
            results["task_2"] = get_api_key()

        async def task_3_check_none():
            # Task 3 should not have any API key set
            await asyncio.sleep(0.005)
            results["task_3"] = get_api_key()

        # Run tasks concurrently using TaskGroup (Python 3.11+)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_1())
            tg.create_task(task_2())
            tg.create_task(task_3_check_none())

        # Verify each task had its own context
        assert results["task_1"] == "task-1-key"
        assert results["task_2"] == "task-2-key"
        assert results["task_3"] is None

    @pytest.mark.asyncio
    async def test_context_scope_within_task(self):
        """Test context scope within a single async task."""

        async def task_with_context_scope():
            # Initially None
            assert get_api_key() is None

            # Set key
            token = set_api_key("scoped-key")
            assert get_api_key() == "scoped-key"

            # Reset using token
            clear_api_key(token)
            assert get_api_key() is None

        await task_with_context_scope()

    def test_multiple_sequential_sets_and_clears(self):
        """Test multiple sequential set/clear operations."""
        clear_api_key()

        # Set first key
        token1 = set_api_key("key-1")
        assert get_api_key() == "key-1"

        # Set second key
        token2 = set_api_key("key-2")
        assert get_api_key() == "key-2"

        # Set third key
        token3 = set_api_key("key-3")
        assert get_api_key() == "key-3"

        # Clear in reverse order
        clear_api_key(token3)
        assert get_api_key() == "key-2"

        clear_api_key(token2)
        assert get_api_key() == "key-1"

        clear_api_key(token1)
        assert get_api_key() is None

    def test_context_token_reset_with_none_value(self):
        """Test token reset works correctly with None values."""
        clear_api_key()

        # Set to "test"
        token1 = set_api_key("test")
        assert get_api_key() == "test"

        # Set to None
        token2 = set_api_key(None)
        assert get_api_key() is None

        # Reset token2 should go back to "test"
        clear_api_key(token2)
        assert get_api_key() == "test"

        # Reset token1 should go back to None
        clear_api_key(token1)
        assert get_api_key() is None

    def test_context_isolation_preserves_values(self):
        """Test that context variables preserve values through operations."""
        clear_api_key()

        api_key = "important-key-xyz"
        token = set_api_key(api_key)

        # Retrieve multiple times
        assert get_api_key() == api_key
        assert get_api_key() == api_key
        assert get_api_key() == api_key

        # Clear and verify
        clear_api_key(token)
        assert get_api_key() is None
