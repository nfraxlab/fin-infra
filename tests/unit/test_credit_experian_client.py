"""Unit tests for Experian HTTP client.

Tests:
- API request methods (get_credit_score, get_credit_report, subscribe_to_changes)
- Error handling (401, 404, 429, 500)
- Retry logic on transient failures
- FCRA permissible purpose headers
- OAuth token injection

Uses pytest-asyncio for async tests and mocking for httpx responses.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from fin_infra.credit.experian.auth import ExperianAuthManager
from fin_infra.credit.experian.client import (
    ExperianAPIError,
    ExperianAuthError,
    ExperianClient,
    ExperianNotFoundError,
    ExperianRateLimitError,
)


class TestExperianClient:
    """Test ExperianClient HTTP client."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "https://sandbox.experian.com"
        self.auth_manager = Mock(spec=ExperianAuthManager)
        self.auth_manager.get_token = AsyncMock(return_value="test_access_token")

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test ExperianClient initialization."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
            timeout=15.0,
        )

        assert client.base_url == self.base_url
        assert client.auth is self.auth_manager
        assert client.timeout == 15.0
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_stripped(self):
        """Test base URL trailing slash is stripped."""
        client = ExperianClient(
            base_url="https://sandbox.experian.com/",
            auth_manager=self.auth_manager,
        )

        assert client.base_url == "https://sandbox.experian.com"

    @pytest.mark.asyncio
    async def test_get_credit_score_success(self):
        """Test get_credit_score makes correct API request."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        # Mock httpx response
        mock_response = Mock()
        mock_response.json.return_value = {
            "creditProfile": {
                "score": 750,
                "scoreModel": "FICO 8",
                "scoreFactor": ["Good payment history"],
                "scoreDate": "2025-11-06",
            }
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_credit_score("user123")

            assert result["creditProfile"]["score"] == 750
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Verify request parameters
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "/consumerservices/credit/v2/scores/user123"
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token"
            assert call_args[1]["headers"]["X-Permissible-Purpose"] == "account_review"

    @pytest.mark.asyncio
    async def test_get_credit_score_custom_purpose(self):
        """Test get_credit_score with custom permissible purpose."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {"creditProfile": {}}
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get_credit_score("user123", permissible_purpose="credit_application")

            call_args = mock_request.call_args
            assert call_args[1]["headers"]["X-Permissible-Purpose"] == "credit_application"

    @pytest.mark.asyncio
    async def test_get_credit_report_success(self):
        """Test get_credit_report makes correct API request."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "creditProfile": {
                "score": {},
                "tradelines": [],
                "inquiries": [],
                "publicRecords": [],
            }
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_credit_report("user123")

            assert "creditProfile" in result
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "/consumerservices/credit/v2/reports/user123"
            assert call_args[1]["headers"]["X-Permissible-Purpose"] == "account_review"

    @pytest.mark.asyncio
    async def test_subscribe_to_changes_success(self):
        """Test subscribe_to_changes makes correct API request."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "subscriptionId": "sub_123",
            "status": "active",
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.subscribe_to_changes(
                "user123",
                "https://example.com/webhook",
                signature_key="secret_key",
            )

            assert result["subscriptionId"] == "sub_123"
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/consumerservices/credit/v2/webhooks"
            assert "json" in call_args[1]
            payload = call_args[1]["json"]
            assert payload["userId"] == "user123"
            assert payload["callbackUrl"] == "https://example.com/webhook"
            assert payload["signatureKey"] == "secret_key"

    @pytest.mark.asyncio
    async def test_subscribe_to_changes_default_events(self):
        """Test subscribe_to_changes uses default events if not provided."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {"subscriptionId": "sub_123"}
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.subscribe_to_changes("user123", "https://example.com/webhook")

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["events"] == ["score_change", "new_inquiry", "new_account"]

    @pytest.mark.asyncio
    async def test_401_auth_error_invalidates_token(self):
        """Test 401 error invalidates token and raises ExperianAuthError."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid token"}}

        mock_error = httpx.HTTPStatusError(
            "Unauthorized",
            request=Mock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error

            with pytest.raises(ExperianAuthError) as exc_info:
                await client.get_credit_score("user123")

            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value)
            # Verify token was invalidated
            self.auth_manager.invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_404_not_found_error(self):
        """Test 404 error raises ExperianNotFoundError."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": {"message": "User not found"}}

        mock_error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error

            with pytest.raises(ExperianNotFoundError) as exc_info:
                await client.get_credit_score("user123")

            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_429_rate_limit_error(self):
        """Test 429 error raises ExperianRateLimitError."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        mock_error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=Mock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error

            with pytest.raises(ExperianRateLimitError) as exc_info:
                await client.get_credit_score("user123")

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_500_server_error(self):
        """Test 500 error raises ExperianAPIError."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal server error"}}

        mock_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error

            with pytest.raises(ExperianAPIError) as exc_info:
                await client.get_credit_score("user123")

            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_without_json(self):
        """Test error handling when response has no JSON body."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("No JSON")

        mock_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error

            with pytest.raises(ExperianAPIError) as exc_info:
                await client.get_credit_score("user123")

            assert exc_info.value.status_code == 500
            # Should still raise error even without JSON response

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """Test client closes httpx connection when used as context manager."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_close:
            async with client:
                pass

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test close() method closes httpx client."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_adds_default_headers(self):
        """Test _request adds default headers (Content-Type, Accept)."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get_credit_score("user123")

            call_args = mock_request.call_args
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_request_merges_additional_headers(self):
        """Test _request merges additional headers with defaults."""
        client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self.auth_manager,
        )

        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Call internal _request with custom headers
            await client._request(
                "GET",
                "/test",
                headers={"X-Custom": "value"},
            )

            call_args = mock_request.call_args
            headers = call_args[1]["headers"]
            assert headers["X-Custom"] == "value"
            assert headers["Authorization"] == "Bearer test_access_token"
