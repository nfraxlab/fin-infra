"""Unit tests for Experian credit provider (real API integration).

Tests for ExperianProvider class:
- Initialization and configuration
- get_credit_score() integration
- get_credit_report() integration
- subscribe_to_changes() integration
- Error handling and retries
- Auth manager integration
- Parser integration
- Context manager
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from fin_infra.credit.experian.provider import ExperianProvider
from fin_infra.models.credit import CreditReport, CreditScore


class TestExperianProvider:
    """Test ExperianProvider class."""

    def test_provider_initialization(self):
        """Test ExperianProvider initializes correctly."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
            base_url="https://sandbox.experian.com",
        )

        assert provider.client_id == "test_client"
        assert provider.client_secret == "test_secret"
        assert provider.base_url == "https://sandbox.experian.com"
        assert provider._client is not None
        assert provider._auth is not None

    def test_provider_default_base_url(self):
        """Test ExperianProvider uses default base URL if not provided."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        assert provider.base_url == "https://sandbox.experian.com"

    @pytest.mark.asyncio
    async def test_get_credit_score_success(self):
        """Test get_credit_score returns parsed CreditScore."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_response_data = {
            "creditProfile": {
                "score": 735,
                "scoreModel": "FICO 8",
                "scoreFactor": ["High utilization", "No late payments"],
                "scoreDate": "2025-11-06",
                "scoreChange": 15,
            }
        }

        with patch.object(
            provider._client, "get_credit_score", new=AsyncMock(return_value=mock_response_data)
        ):
            score = await provider.get_credit_score("user123")

        assert isinstance(score, CreditScore)
        assert score.user_id == "user123"
        assert score.score == 735
        assert score.score_model == "FICO 8"
        assert score.bureau == "experian"
        assert score.score_date == date(2025, 11, 6)
        assert score.factors == ["High utilization", "No late payments"]
        assert score.change == 15

    @pytest.mark.asyncio
    async def test_get_credit_score_custom_purpose(self):
        """Test get_credit_score passes custom permissible purpose."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_response_data = {
            "creditProfile": {
                "score": 700,
                "scoreModel": "FICO 8",
            }
        }

        with patch.object(
            provider._client, "get_credit_score", new=AsyncMock(return_value=mock_response_data)
        ) as mock_get:
            await provider.get_credit_score("user123", permissible_purpose="account_review")

        mock_get.assert_called_once_with("user123", permissible_purpose="account_review")

    @pytest.mark.asyncio
    async def test_get_credit_report_success(self):
        """Test get_credit_report returns parsed CreditReport."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_response_data = {
            "creditProfile": {
                "score": 750,
                "scoreModel": "FICO 8",
                "scoreFactor": ["Good history"],
                "scoreDate": "2025-11-06",
                "tradelines": [
                    {
                        "accountId": "acc_1",
                        "accountType": "credit_card",
                        "creditorName": "Chase",
                        "accountStatus": "open",
                        "currentBalance": "1000.00",
                        "creditLimit": "5000.00",
                        "paymentStatus": "current",
                        "dateOpened": "2020-01-01",
                    }
                ],
                "inquiries": [
                    {
                        "inquiryId": "inq_1",
                        "inquiryType": "hard",
                        "inquirerName": "Chase",
                        "inquiryDate": "2025-01-01",
                    }
                ],
                "publicRecords": [],
                "consumerStatements": ["Test statement"],
            }
        }

        with patch.object(
            provider._client, "get_credit_report", new=AsyncMock(return_value=mock_response_data)
        ):
            report = await provider.get_credit_report("user123")

        assert isinstance(report, CreditReport)
        assert report.user_id == "user123"
        assert report.bureau == "experian"
        assert report.score.score == 750
        assert len(report.accounts) == 1
        assert report.accounts[0].account_id == "acc_1"
        assert report.accounts[0].balance == Decimal("1000.00")
        assert len(report.inquiries) == 1
        assert report.inquiries[0].inquiry_type == "hard"
        assert len(report.public_records) == 0
        assert report.consumer_statements == ["Test statement"]

    @pytest.mark.asyncio
    async def test_get_credit_report_empty_arrays(self):
        """Test get_credit_report handles empty tradelines/inquiries/publicRecords."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_response_data = {
            "creditProfile": {
                "score": 650,
                "scoreModel": "FICO 8",
                "tradelines": [],
                "inquiries": [],
                "publicRecords": [],
            }
        }

        with patch.object(
            provider._client, "get_credit_report", new=AsyncMock(return_value=mock_response_data)
        ):
            report = await provider.get_credit_report("user123")

        assert isinstance(report, CreditReport)
        assert len(report.accounts) == 0
        assert len(report.inquiries) == 0
        assert len(report.public_records) == 0

    @pytest.mark.asyncio
    async def test_subscribe_to_changes_success(self):
        """Test subscribe_to_changes calls client correctly and returns subscription ID."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_response_data = {
            "subscriptionId": "sub_123",
            "userId": "user123",
            "webhookUrl": "https://example.com/webhook",
        }

        with patch.object(
            provider._client, "subscribe_to_changes", new=AsyncMock(return_value=mock_response_data)
        ) as mock_sub:
            result = await provider.subscribe_to_changes(
                "user123",
                "https://example.com/webhook",
                events=["score_change"],
            )

        assert result == "sub_123"  # Provider returns only the subscription ID
        mock_sub.assert_called_once_with(
            "user123",
            "https://example.com/webhook",
            events=["score_change"],
            signature_key=None,
        )

    @pytest.mark.asyncio
    async def test_subscribe_to_changes_default_events(self):
        """Test subscribe_to_changes uses default events if not provided."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        with patch.object(
            provider._client,
            "subscribe_to_changes",
            new=AsyncMock(return_value={"subscriptionId": "sub_123"}),
        ) as mock_sub:
            await provider.subscribe_to_changes("user123", "https://example.com/webhook")

        # Should pass None for events and signature_key (client has default logic)
        mock_sub.assert_called_once_with(
            "user123", "https://example.com/webhook", events=None, signature_key=None
        )

    @pytest.mark.asyncio
    async def test_provider_propagates_client_errors(self):
        """Test provider propagates errors from client."""
        from fin_infra.credit.experian.client import ExperianNotFoundError

        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        with patch.object(
            provider._client,
            "get_credit_score",
            new=AsyncMock(side_effect=ExperianNotFoundError("User not found")),
        ):
            with pytest.raises(ExperianNotFoundError, match="User not found"):
                await provider.get_credit_score("nonexistent_user")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test ExperianProvider works as async context manager."""
        async with ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        ) as provider:
            assert provider._client is not None
            mock_response = {"creditProfile": {"score": 700, "scoreModel": "FICO 8"}}
            with patch.object(
                provider._client, "get_credit_score", new=AsyncMock(return_value=mock_response)
            ):
                score = await provider.get_credit_score("user123")
                assert score.score == 700

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test close() calls _client.close()."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        with patch.object(provider._client, "close", new=AsyncMock()) as mock_close:
            await provider.close()

        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_credit_score_parser_integration(self):
        """Test get_credit_score correctly integrates with parser."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        # Mock response with minimal data
        mock_response_data = {"creditProfile": {}}

        with patch.object(
            provider._client, "get_credit_score", new=AsyncMock(return_value=mock_response_data)
        ):
            score = await provider.get_credit_score("user123")

        # Parser should default score to 300
        assert score.score == 300
        assert score.score_model == "Unknown"
        assert score.bureau == "experian"
        assert score.user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_credit_report_parser_integration(self):
        """Test get_credit_report correctly integrates with parser."""
        provider = ExperianProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        # Mock response with account missing required fields (tests parser defaults)
        mock_response_data = {
            "creditProfile": {
                "score": 720,
                "tradelines": [
                    {
                        "accountId": "acc_min",
                        "accountType": "credit_card",
                        # Missing most fields - parser should use defaults
                    }
                ],
            }
        }

        with patch.object(
            provider._client, "get_credit_report", new=AsyncMock(return_value=mock_response_data)
        ):
            report = await provider.get_credit_report("user123")

        assert len(report.accounts) == 1
        account = report.accounts[0]
        assert account.account_id == "acc_min"
        assert account.account_type == "credit_card"
        assert account.account_status == "open"  # Parser default
        assert account.payment_status == "current"  # Parser default
        assert account.balance == Decimal("0")  # Parser default
