"""Acceptance tests for Experian credit monitoring (real API calls).

Tests real API calls to Experian sandbox with actual credentials.
Skip if EXPERIAN_CLIENT_ID/EXPERIAN_CLIENT_SECRET not set.

Run with:
    pytest tests/acceptance/test_credit_experian_acceptance.py -m acceptance -v

Environment Variables:
    EXPERIAN_CLIENT_ID: Experian OAuth client ID
    EXPERIAN_CLIENT_SECRET: Experian OAuth client secret
    EXPERIAN_ENVIRONMENT: "sandbox" (default) or "production"
"""

import os
import pytest

from fin_infra.credit import easy_credit
from fin_infra.models.credit import CreditScore, CreditReport

# Skip all tests if Experian credentials not available
skip_reason = "Experian credentials not found (set EXPERIAN_CLIENT_ID and EXPERIAN_CLIENT_SECRET)"
credentials_available = bool(
    os.getenv("EXPERIAN_CLIENT_ID") and os.getenv("EXPERIAN_CLIENT_SECRET")
)


@pytest.mark.acceptance
@pytest.mark.skipif(not credentials_available, reason=skip_reason)
@pytest.mark.asyncio
class TestExperianAcceptance:
    """Acceptance tests for Experian API integration."""

    @pytest.fixture
    def credit_provider(self):
        """Create real Experian provider with sandbox credentials."""
        return easy_credit(
            provider="experian",
            use_mock=False,  # Force real API
            environment=os.getenv("EXPERIAN_ENVIRONMENT", "sandbox"),
        )

    async def test_get_credit_score_real_api(self, credit_provider):
        """Test real API call to get credit score from Experian sandbox.

        Verifies:
        - Real API call succeeds
        - Response parses into CreditScore model
        - Score is within valid range (300-850)
        """
        # Test user ID (Experian sandbox may have test user IDs)
        test_user_id = os.getenv("EXPERIAN_TEST_USER_ID", "test_user_123")

        # Make real API call
        score = await credit_provider.get_credit_score(test_user_id)

        # Verify response
        assert isinstance(score, CreditScore)
        assert score.score is not None
        assert 300 <= score.score <= 850, f"Score {score.score} out of valid range"
        assert score.bureau == "experian"

    async def test_get_credit_report_real_api(self, credit_provider):
        """Test real API call to get full credit report from Experian sandbox.

        Verifies:
        - Real API call succeeds
        - Response parses into CreditReport model
        - Report contains expected fields (score, accounts, inquiries)
        """
        # Test user ID
        test_user_id = os.getenv("EXPERIAN_TEST_USER_ID", "test_user_123")

        # Make real API call
        report = await credit_provider.get_credit_report(test_user_id)

        # Verify response
        assert isinstance(report, CreditReport)
        assert report.score is not None
        assert isinstance(report.score, CreditScore)
        assert 300 <= report.score.score <= 850
        assert report.accounts is not None  # May be empty list
        assert isinstance(report.accounts, list)
        assert report.inquiries is not None  # May be empty list
        assert isinstance(report.inquiries, list)

    async def test_error_handling_invalid_credentials(self):
        """Test error handling with invalid credentials.

        Verifies:
        - Invalid credentials raise appropriate error
        - Error message is descriptive
        """
        # Create provider with invalid credentials
        from fin_infra.credit.experian import ExperianProvider

        provider = ExperianProvider(
            client_id="invalid_client_id",
            client_secret="invalid_secret",
            environment="sandbox",
        )

        # Attempt API call (should fail)
        with pytest.raises(Exception) as exc_info:
            await provider.get_credit_score("test_user")

        # Verify error is related to authentication
        error_str = str(exc_info.value).lower()
        assert any(word in error_str for word in ["auth", "unauthorized", "401", "credentials"])

    async def test_rate_limit_handling(self, credit_provider):
        """Test rate limit handling (if sandbox has rate limits).

        Note: This test may be slow or skipped if sandbox doesn't enforce limits.
        """
        # Experian sandbox: 10 requests/minute
        # Make several requests quickly to potentially hit limit
        test_user_id = os.getenv("EXPERIAN_TEST_USER_ID", "test_user_123")

        # Make a few requests (don't hammer the API)
        for i in range(3):
            score = await credit_provider.get_credit_score(test_user_id)
            assert score is not None

        # If we get here, either rate limit not hit or retries succeeded
        # Both are acceptable outcomes

    async def test_credit_score_parsing_from_real_response(self, credit_provider):
        """Test that real API response parses correctly into CreditScore model.

        Verifies all expected fields are present and valid.
        """
        test_user_id = os.getenv("EXPERIAN_TEST_USER_ID", "test_user_123")

        score = await credit_provider.get_credit_score(test_user_id)

        # Verify all CreditScore fields
        assert score.score is not None
        assert isinstance(score.score, int)
        assert score.bureau == "experian"
        # report_date may be None or datetime
        # factors may be None or list

    async def test_credit_report_parsing_from_real_response(self, credit_provider):
        """Test that real API response parses correctly into CreditReport model.

        Verifies all expected fields are present and valid.
        """
        test_user_id = os.getenv("EXPERIAN_TEST_USER_ID", "test_user_123")

        report = await credit_provider.get_credit_report(test_user_id)

        # Verify all CreditReport fields
        assert report.score is not None
        assert isinstance(report.score, CreditScore)
        assert report.accounts is not None
        assert isinstance(report.accounts, list)
        assert report.inquiries is not None
        assert isinstance(report.inquiries, list)
        # public_records may be None or list
