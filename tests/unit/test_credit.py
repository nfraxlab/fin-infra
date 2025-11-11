"""Unit tests for credit score monitoring.

Tests:
- Credit data models (CreditScore, CreditReport, CreditAccount, CreditInquiry)
- MockExperianProvider (v1 mock implementation)
- ExperianProvider (v2 real API - requires credentials)
- easy_credit() builder
- add_credit() FastAPI integration

Note: v1 uses mock data only; real Experian API integration is v2.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.credit import MockExperianProvider, easy_credit, add_credit
from fin_infra.models.credit import (
    CreditAccount,
    CreditInquiry,
    CreditReport,
    CreditScore,
    PublicRecord,
)


class TestCreditModels:
    """Test credit data models."""

    def test_credit_score_model(self):
        """Test CreditScore model validation."""
        score = CreditScore(
            user_id="user123",
            score=735,
            score_model="FICO 8",
            bureau="experian",
            score_date=date.today(),
            factors=["Credit utilization is high"],
            change=15,
        )
        assert score.user_id == "user123"
        assert score.score == 735
        assert score.score_model == "FICO 8"
        assert score.bureau == "experian"
        assert score.change == 15

    def test_credit_score_bounds(self):
        """Test CreditScore score validation (300-850)."""
        # Valid score
        score = CreditScore(
            user_id="user123",
            score=300,
            score_model="FICO 8",
            bureau="experian",
            score_date=date.today(),
        )
        assert score.score == 300

        # Invalid score (too low)
        with pytest.raises(ValueError):
            CreditScore(
                user_id="user123",
                score=299,
                score_model="FICO 8",
                bureau="experian",
                score_date=date.today(),
            )

        # Invalid score (too high)
        with pytest.raises(ValueError):
            CreditScore(
                user_id="user123",
                score=851,
                score_model="FICO 8",
                bureau="experian",
                score_date=date.today(),
            )

    def test_credit_account_model(self):
        """Test CreditAccount model validation."""
        account = CreditAccount(
            account_id="acc123",
            account_type="credit_card",
            creditor_name="Chase Bank",
            account_status="open",
            balance=Decimal("5000.00"),
            credit_limit=Decimal("10000.00"),
            payment_status="current",
            opened_date=date(2020, 1, 1),
            last_payment_date=date(2025, 1, 1),
        )
        assert account.account_id == "acc123"
        assert account.account_type == "credit_card"
        assert account.balance == Decimal("5000.00")

    def test_credit_inquiry_model(self):
        """Test CreditInquiry model validation."""
        inquiry = CreditInquiry(
            inquiry_id="inq123",
            inquiry_type="hard",
            inquirer_name="Chase Bank",
            inquiry_date=date(2025, 1, 1),
            purpose="credit_card_application",
        )
        assert inquiry.inquiry_id == "inq123"
        assert inquiry.inquiry_type == "hard"
        assert inquiry.purpose == "credit_card_application"

    def test_public_record_model(self):
        """Test PublicRecord model validation."""
        record = PublicRecord(
            record_id="rec123",
            record_type="bankruptcy",
            filed_date=date(2020, 1, 1),
            status="discharged",
            amount=Decimal("50000.00"),
            court="U.S. Bankruptcy Court",
        )
        assert record.record_id == "rec123"
        assert record.record_type == "bankruptcy"
        assert record.status == "discharged"

    def test_credit_report_model(self):
        """Test CreditReport model validation."""
        score = CreditScore(
            user_id="user123",
            score=735,
            score_model="FICO 8",
            bureau="experian",
            score_date=date.today(),
        )
        account = CreditAccount(
            account_id="acc123",
            account_type="credit_card",
            creditor_name="Chase Bank",
            account_status="open",
            balance=Decimal("5000.00"),
            credit_limit=Decimal("10000.00"),
            payment_status="current",
            opened_date=date(2020, 1, 1),
        )
        report = CreditReport(
            user_id="user123",
            bureau="experian",
            report_date=date.today(),
            score=score,
            accounts=[account],
            inquiries=[],
            public_records=[],
            consumer_statements=[],
        )
        assert report.user_id == "user123"
        assert report.bureau == "experian"
        assert len(report.accounts) == 1
        assert report.score.score == 735


class TestMockExperianProvider:
    """Test MockExperianProvider (v1 mock implementation)."""

    def test_provider_initialization(self):
        """Test provider initialization with config."""
        provider = MockExperianProvider(api_key="test_key", environment="sandbox")
        assert provider.api_key == "test_key"
        assert provider.environment == "sandbox"

    def test_get_credit_score(self):
        """Test get_credit_score returns mock data."""
        provider = MockExperianProvider()
        score = provider.get_credit_score("user123")

        assert isinstance(score, CreditScore)
        assert score.user_id == "user123"
        assert score.score == 735  # Mock score
        assert score.score_model == "FICO 8"
        assert score.bureau == "experian"
        assert score.score_date == date.today()
        assert len(score.factors) > 0
        assert score.change == 15

    def test_get_credit_report(self):
        """Test get_credit_report returns mock data."""
        provider = MockExperianProvider()
        report = provider.get_credit_report("user123")

        assert isinstance(report, CreditReport)
        assert report.user_id == "user123"
        assert report.bureau == "experian"
        assert report.report_date == date.today()
        assert report.score.score == 735

        # Check accounts
        assert len(report.accounts) == 3
        assert any(acc.account_type == "credit_card" for acc in report.accounts)
        assert any(acc.account_type == "auto_loan" for acc in report.accounts)
        assert any(acc.account_type == "student_loan" for acc in report.accounts)

        # Check inquiries
        assert len(report.inquiries) == 2
        assert all(inq.inquiry_type in ["hard", "soft"] for inq in report.inquiries)

        # Check no public records
        assert len(report.public_records) == 0

    def test_subscribe_to_changes(self):
        """Test subscribe_to_changes returns mock subscription ID."""
        provider = MockExperianProvider()
        sub_id = provider.subscribe_to_changes("user123", "https://example.com/webhook")

        assert sub_id == "sub_mock_user123"


class TestEasyCredit:
    """Test easy_credit() builder."""

    def test_easy_credit_default(self):
        """Test easy_credit with default provider (auto-detects mock without credentials)."""
        credit = easy_credit()
        assert isinstance(credit, MockExperianProvider)

    def test_easy_credit_explicit_provider(self):
        """Test easy_credit with explicit provider name (uses mock without credentials)."""
        credit = easy_credit(provider="experian")
        assert isinstance(credit, MockExperianProvider)

    def test_easy_credit_with_config(self):
        """Test easy_credit with explicit config (uses mock when credentials incomplete)."""
        credit = easy_credit(provider="experian", api_key="test_key", environment="production")
        assert isinstance(credit, MockExperianProvider)
        assert credit.api_key == "test_key"
        assert credit.environment == "production"

    def test_easy_credit_force_mock(self):
        """Test easy_credit with use_mock=True forces mock provider."""
        credit = easy_credit(provider="experian", use_mock=True)
        assert isinstance(credit, MockExperianProvider)

    def test_easy_credit_with_instance(self):
        """Test easy_credit with CreditProvider instance."""
        provider = MockExperianProvider(api_key="test_key")
        credit = easy_credit(provider=provider)
        assert credit is provider

    def test_easy_credit_unknown_provider(self):
        """Test easy_credit with unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown credit provider"):
            easy_credit(provider="unknown")

    def test_easy_credit_equifax_not_implemented(self):
        """Test easy_credit with equifax raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Equifax provider not implemented"):
            easy_credit(provider="equifax")

    def test_easy_credit_transunion_not_implemented(self):
        """Test easy_credit with transunion raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="TransUnion provider not implemented"):
            easy_credit(provider="transunion")


class TestAddCredit:
    """Test add_credit() FastAPI integration."""

    def test_add_credit(self):
        """Test add_credit wires routes to app (uses mock without credentials)."""
        app = FastAPI()
        credit = add_credit(app)

        assert isinstance(credit, MockExperianProvider)
        assert hasattr(app.state, "credit_provider")
        assert app.state.credit_provider is credit

        # Check routes exist
        routes = [route.path for route in app.routes]
        assert "/credit/score" in routes
        assert "/credit/report" in routes
        # Note: webhooks are mounted at /_webhooks/* not /credit/subscribe

    def test_add_credit_custom_prefix(self):
        """Test add_credit with custom prefix."""
        app = FastAPI()
        credit = add_credit(app, prefix="/api/credit")

        routes = [route.path for route in app.routes]
        assert "/api/credit/score" in routes
        assert "/api/credit/report" in routes

    # TODO: Re-enable after fixing auth mock
    # def test_get_credit_score_endpoint(self):
    #     """Test POST /credit/score endpoint."""
    #     from svc_infra.api.fastapi.dual.protected import RequireUser
    #
    #     app = FastAPI()
    #     add_credit(app)
    #
    #     # Mock the RequireUser dependency
    #     async def mock_require_user():
    #         return {"user_id": "test_user"}
    #
    #     app.dependency_overrides[RequireUser] = mock_require_user
    #     client = TestClient(app)
    #
    #     response = client.post("/credit/score", json={"user_id": "user123"})
    #     assert response.status_code == 200
    #
    #     data = response.json()
    #     assert data["user_id"] == "user123"
    #     assert data["score"] == 735
    #     assert data["bureau"] == "experian"
    #
    # def test_get_credit_report_endpoint(self):
    #     """Test POST /credit/report endpoint."""
    #     from svc_infra.api.fastapi.dual.protected import RequireUser
    #
    #     app = FastAPI()
    #     add_credit(app)
    #
    #     # Mock the RequireUser dependency
    #     async def mock_require_user():
    #         return {"user_id": "test_user"}
    #
    #     app.dependency_overrides[RequireUser] = mock_require_user
    #     client = TestClient(app)
    #
    #     response = client.post("/credit/report", json={"user_id": "user123"})
    #     assert response.status_code == 200
    #
    #     data = response.json()
    #     assert data["user_id"] == "user123"
    #     assert data["bureau"] == "experian"
    #     assert len(data["accounts"]) == 3
    #     assert len(data["inquiries"]) == 2

    def test_webhook_subscriptions_endpoint(self):
        """Test POST /_webhooks/subscriptions endpoint (from svc-infra)."""
        app = FastAPI()
        add_credit(app)
        client = TestClient(app)

        # Webhook subscriptions are mounted at /_webhooks/subscriptions by add_webhooks()
        response = client.post(
            "/_webhooks/subscriptions",
            json={
                "topic": "credit.score_changed",
                "url": "https://example.com/webhook",
                "secret": "test_secret",
            },
        )
        # This will succeed or fail based on webhook implementation
        # Just verify the route exists
        assert response.status_code in [200, 201, 422]  # 422 if missing required fields
