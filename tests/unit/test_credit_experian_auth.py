"""Unit tests for Experian OAuth 2.0 authentication manager (svc-infra cache integration).

Tests:
- Token acquisition (client credentials flow)
- svc-infra cache integration (@cache_read decorator)
- Tag-based invalidation
- Error handling (invalid credentials, network errors)

Note: Tests mock svc-infra cache decorator to avoid Redis dependency.
Uses pytest-asyncio for async tests and unittest.mock for HTTP mocking.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from svc_infra.cache import init_cache
from svc_infra.cache.tags import invalidate_tags

from fin_infra.credit.experian.auth import ExperianAuthManager


# Initialize cache once for all tests (uses in-memory backend for tests)
init_cache(url="mem://", prefix="test")


class TestExperianAuthManager:
    """Test ExperianAuthManager with svc-infra cache integration."""

    # Setup test credentials
    client_id = "test_client_id"
    client_secret = "test_client_secret"
    base_url = "https://sandbox.experian.com"

    def setup_method(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.base_url = "https://sandbox.experian.com"

    async def asyncTearDown(self):
        """Clear cache after each test."""

        await invalidate_tags("oauth:experian")

    def test_auth_manager_initialization(self):
        """Test ExperianAuthManager initialization."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        assert auth.client_id == self.client_id
        assert auth.client_secret == self.client_secret
        assert auth.base_url == self.base_url
        assert auth.token_ttl == 3600

    def test_base_url_trailing_slash_stripped(self):
        """Test base_url trailing slash is stripped."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url="https://sandbox.experian.com/",
        )

        assert auth.base_url == "https://sandbox.experian.com"

    def test_custom_token_ttl(self):
        """Test custom token TTL is set."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
            token_ttl=7200,
        )

        assert auth.token_ttl == 7200

    @pytest.mark.asyncio
    async def test_get_token_cache_miss_fetches_new_token(self):
        """Test get_token fetches new token on cache miss."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        mock_token = "test_access_token_123"
        mock_response_data = {
            "access_token": mock_token,
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        # Mock httpx.AsyncClient to return token response
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # get_token() will hit the cache decorator, which will call _fetch_token on cache miss
            # Since cache is not initialized in tests, it will always call the wrapped function
            token = await auth.get_token()

        assert token == mock_token
        # Verify OAuth request was made
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/oauth2/v1/token" in call_args[0][0]
        assert call_args[1]["data"]["grant_type"] == "client_credentials"

    @pytest.mark.asyncio
    async def test_get_token_with_http_error(self):
        """Test get_token handles HTTP errors (401 Unauthorized)."""
        # Use unique client_id to avoid cache hit from previous test
        auth = ExperianAuthManager(
            client_id="unique_client_id_for_error_test",  # Unique ID
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        # Mock httpx.AsyncClient to raise 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=mock_response,
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await auth.get_token()

    @pytest.mark.asyncio
    async def test_fetch_token_encodes_credentials_correctly(self):
        """Test _fetch_token encodes client credentials as base64."""
        auth = ExperianAuthManager(
            client_id="my_client",
            client_secret="my_secret",
            base_url=self.base_url,
        )

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "token123"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await auth._fetch_token()

        # Verify Authorization header contains base64-encoded credentials
        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

        # Decode and verify
        import base64

        encoded = headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "my_client:my_secret"

    @pytest.mark.asyncio
    async def test_invalidate_calls_invalidate_tags_for_client(self):
        """Test invalidate() calls svc-infra invalidate_tags for specific client."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        # Mock the invalidate_tags function at the source module
        with patch("svc_infra.cache.tags.invalidate_tags", new=AsyncMock()) as mock_invalidate:
            await auth.invalidate()

        # Verify invalidate_tags was called with client-specific tag
        mock_invalidate.assert_called_once_with(f"oauth:experian:{self.client_id}")

    @pytest.mark.asyncio
    async def test_get_token_returns_string(self):
        """Test get_token returns string token."""
        # Use unique client_id to avoid cache hit from previous test
        auth = ExperianAuthManager(
            client_id="unique_client_id_for_string_test",  # Unique ID
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "test_token_string"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            token = await auth.get_token()

        assert isinstance(token, str)
        assert token == "test_token_string"

    @pytest.mark.asyncio
    async def test_fetch_token_posts_to_correct_endpoint(self):
        """Test _fetch_token makes POST request to correct OAuth endpoint."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url="https://api.experian.com",
        )

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "token"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await auth._fetch_token()

        # Verify correct endpoint
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://api.experian.com/oauth2/v1/token"

    @pytest.mark.asyncio
    async def test_fetch_token_includes_scope(self):
        """Test _fetch_token includes required OAuth scope."""
        auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "token"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await auth._fetch_token()

        # Verify scope is included in request
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]
        assert "scope" in data
        assert "read:credit" in data["scope"]
        assert "write:credit" in data["scope"]
