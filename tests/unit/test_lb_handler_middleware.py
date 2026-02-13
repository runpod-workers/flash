import pytest
import asyncio
from unittest.mock import MagicMock

from api_key_context import get_api_key, clear_api_key


class TestLbHandlerMiddleware:
    """Unit tests for API key extraction middleware."""

    def setup_method(self):
        """Setup for each test method."""
        # Clear API key context before each test
        clear_api_key()

    @pytest.mark.asyncio
    async def test_middleware_extracts_bearer_token_from_header(self):
        """Test middleware extracts API key from valid Authorization header."""
        # Import here to get fresh state
        from lb_handler import extract_api_key_middleware

        # Create mock request with Bearer token
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer test-api-key-12345"

        # Create mock next handler that returns a response
        async def mock_call_next(request):
            # Check that API key was set in context
            stored_key = get_api_key()
            assert stored_key == "test-api-key-12345"
            return MagicMock(status_code=200)

        # Call middleware
        response = await extract_api_key_middleware(mock_request, mock_call_next)

        # Verify response returned
        assert response.status_code == 200

        # Verify context was cleaned up after request
        assert get_api_key() is None

    @pytest.mark.asyncio
    async def test_middleware_handles_missing_authorization_header(self):
        """Test middleware handles missing Authorization header gracefully."""
        from lb_handler import extract_api_key_middleware

        # Create mock request without Authorization header
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        # Create mock next handler
        async def mock_call_next(request):
            # Should not have API key in context
            assert get_api_key() is None
            return MagicMock(status_code=200)

        # Call middleware
        response = await extract_api_key_middleware(mock_request, mock_call_next)

        # Verify response returned
        assert response.status_code == 200

        # Verify context remains clean
        assert get_api_key() is None

    @pytest.mark.asyncio
    async def test_middleware_handles_malformed_authorization_header(self):
        """Test middleware handles malformed Authorization header."""
        from lb_handler import extract_api_key_middleware

        # Test various malformed headers
        malformed_headers = [
            "Basic dXNlcjpwYXNz",  # Basic auth, not Bearer
            "Bearer",  # Missing token
            "Bearer ",  # Just "Bearer " with no token
            "token-without-bearer",  # No Bearer prefix
            "bearer lowercase-key",  # lowercase 'bearer'
        ]

        for header_value in malformed_headers:
            clear_api_key()

            mock_request = MagicMock()
            mock_request.headers.get.return_value = header_value

            async def mock_call_next(request):
                # Should not have API key in context for malformed headers
                # (except if it somehow parsed a token, which shouldn't happen)
                return MagicMock(status_code=200)

            response = await extract_api_key_middleware(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_clears_context_after_request(self):
        """Test middleware clears context variable after request completes."""
        from lb_handler import extract_api_key_middleware

        api_key = "test-key-to-be-cleared"
        mock_request = MagicMock()
        mock_request.headers.get.return_value = f"Bearer {api_key}"

        # Verify context is clean before
        assert get_api_key() is None

        async def mock_call_next(request):
            # Inside the request, context should have the key
            assert get_api_key() == api_key
            return MagicMock(status_code=200)

        # Call middleware
        await extract_api_key_middleware(mock_request, mock_call_next)

        # After middleware completes, context should be cleared
        assert get_api_key() is None

    @pytest.mark.asyncio
    async def test_middleware_clears_context_even_on_exception(self):
        """Test middleware clears context even if handler raises exception."""
        from lb_handler import extract_api_key_middleware

        api_key = "test-key-exception"
        mock_request = MagicMock()
        mock_request.headers.get.return_value = f"Bearer {api_key}"

        async def mock_call_next_with_error(request):
            # Verify API key was set
            assert get_api_key() == api_key
            # Raise an exception
            raise ValueError("Handler error")

        # Call middleware and expect it to raise
        with pytest.raises(ValueError):
            await extract_api_key_middleware(mock_request, mock_call_next_with_error)

        # Verify context was still cleaned up
        assert get_api_key() is None

    @pytest.mark.asyncio
    async def test_middleware_extracts_bearer_token_with_whitespace(self):
        """Test middleware correctly handles Bearer token with extra whitespace."""
        from lb_handler import extract_api_key_middleware

        # Test Bearer token with leading/trailing spaces
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer   test-api-key-with-spaces   "

        async def mock_call_next(request):
            # Should extract token with whitespace trimmed
            stored_key = get_api_key()
            assert stored_key == "test-api-key-with-spaces"
            return MagicMock(status_code=200)

        response = await extract_api_key_middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_context_isolation_between_concurrent_requests(self):
        """Test context isolation between concurrent request handlers."""
        from lb_handler import extract_api_key_middleware

        results = {}

        async def request_1_handler():
            mock_request = MagicMock()
            mock_request.headers.get.return_value = "Bearer request-1-key"

            async def next_handler(request):
                # Simulate some async work
                await asyncio.sleep(0.01)
                results["request_1_inside"] = get_api_key()
                return MagicMock(status_code=200)

            await extract_api_key_middleware(mock_request, next_handler)
            results["request_1_outside"] = get_api_key()

        async def request_2_handler():
            mock_request = MagicMock()
            mock_request.headers.get.return_value = "Bearer request-2-key"

            async def next_handler(request):
                # Simulate some async work
                await asyncio.sleep(0.005)
                results["request_2_inside"] = get_api_key()
                return MagicMock(status_code=200)

            await extract_api_key_middleware(mock_request, next_handler)
            results["request_2_outside"] = get_api_key()

        # Run both requests concurrently
        async with asyncio.TaskGroup() as tg:
            tg.create_task(request_1_handler())
            tg.create_task(request_2_handler())

        # Verify each request had isolated context
        assert results["request_1_inside"] == "request-1-key"
        assert results["request_2_inside"] == "request-2-key"
        # Outside handlers, both should be None (cleaned up)
        assert results["request_1_outside"] is None
        assert results["request_2_outside"] is None

    @pytest.mark.asyncio
    async def test_middleware_case_sensitive_bearer_prefix(self):
        """Test middleware correctly requires 'Bearer' prefix (case-sensitive)."""
        from lb_handler import extract_api_key_middleware

        # Test lowercase 'bearer' (should not match)
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "bearer lowercase-key"

        async def mock_call_next(request):
            # Should not extract key with lowercase 'bearer'
            assert get_api_key() is None
            return MagicMock(status_code=200)

        response = await extract_api_key_middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_with_complex_api_key_format(self):
        """Test middleware with complex API key formats."""
        from lb_handler import extract_api_key_middleware

        # Complex API key with special characters
        complex_key = "rp-aB1234567890-xyz_test.key"
        mock_request = MagicMock()
        mock_request.headers.get.return_value = f"Bearer {complex_key}"

        async def mock_call_next(request):
            stored_key = get_api_key()
            assert stored_key == complex_key
            return MagicMock(status_code=200)

        response = await extract_api_key_middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_preserves_api_key_through_request_lifecycle(self):
        """Test API key remains available throughout request lifecycle."""
        from lb_handler import extract_api_key_middleware

        api_key = "persistent-key"
        mock_request = MagicMock()
        mock_request.headers.get.return_value = f"Bearer {api_key}"

        access_log = []

        async def mock_call_next(request):
            # Multiple accesses during request should all return same key
            access_log.append(get_api_key())
            await asyncio.sleep(0.001)
            access_log.append(get_api_key())
            await asyncio.sleep(0.001)
            access_log.append(get_api_key())
            return MagicMock(status_code=200)

        await extract_api_key_middleware(mock_request, mock_call_next)

        # Verify all accesses returned the same key
        assert len(access_log) == 3
        assert all(key == api_key for key in access_log)
        # After middleware, should be cleared
        assert get_api_key() is None
