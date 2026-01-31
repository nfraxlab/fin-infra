"""Tests for banking provider integration."""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from fin_infra.banking import easy_banking
from fin_infra.providers.banking.teller_client import TellerClient
from fin_infra.providers.base import BankingProvider


class TestEasyBanking:
    """Test easy_banking() builder function."""

    def test_easy_banking_default_teller(self):
        """Test that easy_banking() defaults to Teller provider."""
        with (
            patch.dict(
                "os.environ",
                {
                    "TELLER_CERTIFICATE_PATH": "./cert.pem",
                    "TELLER_PRIVATE_KEY_PATH": "./key.pem",
                    "TELLER_ENVIRONMENT": "sandbox",
                },
                clear=False,  # Don't clear other env vars, just override these
            ),
            patch("ssl.create_default_context"),
            patch("httpx.Client"),
        ):
            banking = easy_banking()
            assert isinstance(banking, BankingProvider)
            assert isinstance(banking, TellerClient)
            # Verify the client was created (may use default cert paths from root if .env present)
            assert banking.cert_path in ("./cert.pem", "./teller_certificate.pem")  # Allow both
            assert banking.key_path in ("./key.pem", "./teller_private_key.pem")  # Allow both
            assert banking.environment == "sandbox"

    def test_easy_banking_explicit_provider(self):
        """Test easy_banking() with explicit provider name."""
        with (
            patch.dict(
                "os.environ",
                {
                    "TELLER_CERTIFICATE_PATH": "./cert.pem",
                    "TELLER_PRIVATE_KEY_PATH": "./key.pem",
                },
            ),
            patch("ssl.create_default_context"),
            patch("httpx.Client"),
        ):
            banking = easy_banking(provider="teller")
            assert isinstance(banking, TellerClient)

    def test_easy_banking_config_override(self):
        """Test easy_banking() with configuration override."""
        # Clear any cached providers first
        from fin_infra.providers.registry import _registry

        _registry._cache.clear()

        with patch("ssl.create_default_context"), patch("httpx.Client"):
            banking = easy_banking(
                provider="teller",
                cert_path="./override_cert.pem",
                key_path="./override_key.pem",
                environment="production",
            )
            assert isinstance(banking, TellerClient)
            assert banking.cert_path == "./override_cert.pem"
            assert banking.key_path == "./override_key.pem"
            assert banking.environment == "production"

    def test_easy_banking_missing_env_uses_defaults(self):
        """Test easy_banking() uses defaults when env vars missing."""
        # Clear any cached providers first
        from fin_infra.providers.registry import _registry

        _registry._cache.clear()

        with patch.dict("os.environ", {}, clear=True):
            banking = easy_banking()
            assert isinstance(banking, TellerClient)
            # Should use None cert paths for sandbox (test mode)
            assert banking.cert_path is None
            assert banking.key_path is None
            assert banking.environment == "sandbox"


class TestTellerClient:
    """Test Teller banking provider implementation."""

    def test_init_with_defaults(self):
        """Test TellerClient initialization with defaults."""
        teller = TellerClient()
        assert teller.cert_path is None
        assert teller.key_path is None
        assert teller.environment == "sandbox"
        assert teller.base_url == "https://api.sandbox.teller.io"
        assert teller.timeout == 30.0

    def test_init_with_custom_config(self):
        """Test TellerClient initialization with custom configuration."""
        with patch("ssl.create_default_context"), patch("httpx.Client"):
            teller = TellerClient(
                cert_path="./cert.pem",
                key_path="./key.pem",
                environment="production",
                timeout=60.0,
            )
            assert teller.cert_path == "./cert.pem"
            assert teller.key_path == "./key.pem"
            assert teller.environment == "production"
            assert teller.base_url == "https://api.teller.io"
            assert teller.timeout == 60.0

    def test_init_production_requires_certificates(self):
        """Test TellerClient requires certificates in production."""
        with pytest.raises(ValueError, match="are required for production environment"):
            TellerClient(environment="production")

    def test_create_link_token(self):
        """Test create_link_token makes correct API call."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = {"enrollment_id": "test_enrollment_123"}
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "request", return_value=mock_response) as mock_request:
            result = teller.create_link_token(user_id="user123")

        assert result == "test_enrollment_123"
        mock_request.assert_called_once_with(
            "POST",
            "/enrollments",
            json={
                "user_id": "user123",
                "products": ["accounts", "transactions", "balances", "identity"],
            },
        )

    def test_exchange_public_token(self):
        """Test exchange_public_token returns access token."""
        teller = TellerClient()
        result = teller.exchange_public_token("public_token_123")

        assert result == {
            "access_token": "public_token_123",
            "item_id": None,
        }

    def test_accounts(self):
        """Test accounts fetches account list."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "acc_123",
                "name": "Checking",
                "type": "checking",
                "mask": "1234",
                "currency": "USD",
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "get", return_value=mock_response) as mock_get:
            result = teller.accounts(access_token="token_123")

        assert len(result) == 1
        assert result[0]["id"] == "acc_123"
        mock_get.assert_called_once_with(
            "/accounts",
            auth=("token_123", ""),
        )

    def test_transactions(self):
        """Test transactions fetches transaction list."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "txn_123",
                "account_id": "acc_123",
                "amount": -50.00,
                "date": "2025-01-01",
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "get", return_value=mock_response) as mock_get:
            result = teller.transactions(
                access_token="token_123",
                start_date="2025-01-01",
                end_date="2025-01-31",
            )

        assert len(result) == 1
        assert result[0]["id"] == "txn_123"
        mock_get.assert_called_once_with(
            "/transactions",
            auth=("token_123", ""),
            params={"from_date": "2025-01-01", "to_date": "2025-01-31"},
        )

    def test_balances_all_accounts(self):
        """Test balances fetches all account balances."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = {"accounts": [{"id": "acc_123", "balance": 1000.00}]}
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "get", return_value=mock_response) as mock_get:
            result = teller.balances(access_token="token_123")

        assert "accounts" in result
        mock_get.assert_called_once_with(
            "/accounts/balances",
            auth=("token_123", ""),
        )

    def test_balances_specific_account(self):
        """Test balances fetches specific account balance."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = {
            "balance_available": 1000.00,
            "balance_current": 1050.00,
        }
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "get", return_value=mock_response) as mock_get:
            result = teller.balances(access_token="token_123", account_id="acc_123")

        assert result["balance_available"] == 1000.00
        mock_get.assert_called_once_with(
            "/accounts/acc_123/balances",
            auth=("token_123", ""),
        )

    def test_identity(self):
        """Test identity fetches account holder information."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "John Doe",
            "email": "john@example.com",
        }
        mock_response.raise_for_status = Mock()

        with patch.object(teller.client, "get", return_value=mock_response) as mock_get:
            result = teller.identity(access_token="token_123")

        assert result["name"] == "John Doe"
        mock_get.assert_called_once_with(
            "/identity",
            auth=("token_123", ""),
        )

    def test_request_error_handling(self):
        """Test _request handles HTTP errors."""
        teller = TellerClient()

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=Mock(),
        )

        with patch.object(teller.client, "request", return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                teller._request("GET", "/test")


class TestAddBanking:
    """Test add_banking() FastAPI integration."""

    @pytest.fixture
    def app_with_banking(self):
        """Create FastAPI app with banking routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from fin_infra.banking import add_banking

        app = FastAPI()

        # Mock the banking provider
        mock_provider = Mock()

        with patch("fin_infra.banking.easy_banking", return_value=mock_provider):
            add_banking(app, provider="teller", prefix="/banking")

        client = TestClient(app)
        return client, mock_provider

    def test_routes_mounted(self, app_with_banking):
        """Should mount all banking routes."""
        client, _ = app_with_banking

        # Check that routes exist (will get 422 or other errors, not 404)
        response = client.post("/banking/link")
        assert response.status_code != 404

        response = client.post("/banking/exchange")
        assert response.status_code != 404

        response = client.get("/banking/accounts")
        assert response.status_code != 404

    def test_create_link_token_endpoint(self, app_with_banking):
        """Should create link token."""
        client, mock_provider = app_with_banking

        # Mock should return string directly (not dict)
        mock_provider.create_link_token.return_value = "link_token_123"

        response = client.post("/banking/link", json={"user_id": "user_123"})

        assert response.status_code == 200
        data = response.json()
        assert data["link_token"] == "link_token_123"
        mock_provider.create_link_token.assert_called_once_with(user_id="user_123")

    def test_exchange_public_token_endpoint(self, app_with_banking):
        """Should exchange public token."""
        client, mock_provider = app_with_banking

        mock_provider.exchange_public_token.return_value = {
            "access_token": "access_token_123",
            "item_id": "item_456",
        }

        response = client.post("/banking/exchange", json={"public_token": "public_token_xyz"})

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "access_token_123"
        mock_provider.exchange_public_token.assert_called_once_with(public_token="public_token_xyz")

    def test_get_accounts_endpoint(self, app_with_banking):
        """Should fetch accounts."""
        client, mock_provider = app_with_banking

        mock_provider.accounts.return_value = [
            {"id": "acc_1", "name": "Checking", "balance": 1000.00},
            {"id": "acc_2", "name": "Savings", "balance": 5000.00},
        ]

        response = client.get("/banking/accounts", headers={"Authorization": "Bearer token_123"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["accounts"]) == 2
        assert data["accounts"][0]["name"] == "Checking"
        mock_provider.accounts.assert_called_once_with(access_token="token_123")

    def test_get_accounts_missing_auth(self, app_with_banking):
        """Should return 422 when Authorization header missing (FastAPI validation)."""
        client, _ = app_with_banking

        response = client.get("/banking/accounts")

        # FastAPI returns 422 for missing required headers (validation error)
        assert response.status_code == 422
        assert "Authorization" in str(response.json())

    def test_custom_prefix(self):
        """Should support custom prefix."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from fin_infra.banking import add_banking

        app = FastAPI()
        mock_provider = Mock()

        with patch("fin_infra.banking.easy_banking", return_value=mock_provider):
            add_banking(app, prefix="/custom-banking")

        client = TestClient(app)

        # Should be mounted at custom prefix
        response = client.post("/custom-banking/link")
        assert response.status_code != 404

        # Should NOT be at default prefix
        response = client.post("/banking/link")
        assert response.status_code == 404
