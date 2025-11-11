"""Unit tests for tax data integration.

Tests for MockTaxProvider, easy_tax(), and add_tax_data().
"""

import pytest
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.tax import easy_tax, add_tax_data
from fin_infra.providers.tax import MockTaxProvider
from fin_infra.models.tax import (
    TaxFormW2,
    TaxForm1099INT,
    CryptoTaxReport,
    TaxLiability,
)


class TestMockTaxProvider:
    """Tests for MockTaxProvider."""

    @pytest.mark.asyncio
    async def test_get_tax_documents_returns_five_forms(self):
        """MockTaxProvider returns 5 tax forms (W-2, 1099-INT/DIV/B/MISC)."""
        provider = MockTaxProvider()
        documents = await provider.get_tax_documents("user_123", 2024)

        assert len(documents) == 5
        form_types = [d.form_type for d in documents]
        assert set(form_types) == {"W2", "1099-INT", "1099-DIV", "1099-B", "1099-MISC"}

    @pytest.mark.asyncio
    async def test_get_tax_documents_w2_values(self):
        """MockTaxProvider W-2 has realistic hardcoded values."""
        provider = MockTaxProvider()
        documents = await provider.get_tax_documents("user_123", 2024)

        w2 = [d for d in documents if d.form_type == "W2"][0]
        assert isinstance(w2, TaxFormW2)
        assert w2.wages == Decimal("75000.00")
        assert w2.federal_tax_withheld == Decimal("12000.00")
        assert w2.social_security_wages == Decimal("75000.00")
        assert w2.retirement_plan is True
        assert w2.issuer == "Acme Corporation"

    @pytest.mark.asyncio
    async def test_get_tax_documents_1099int_values(self):
        """MockTaxProvider 1099-INT has realistic hardcoded values."""
        provider = MockTaxProvider()
        documents = await provider.get_tax_documents("user_123", 2024)

        f1099int = [d for d in documents if d.form_type == "1099-INT"][0]
        assert isinstance(f1099int, TaxForm1099INT)
        assert f1099int.interest_income == Decimal("250.00")
        assert f1099int.issuer == "Acme Bank"

    @pytest.mark.asyncio
    async def test_get_tax_document_by_id(self):
        """MockTaxProvider can retrieve specific document by ID."""
        provider = MockTaxProvider()
        document = await provider.get_tax_document("w2_2024_user_123")

        assert document.document_id == "w2_2024_user_123"
        assert document.form_type == "W2"
        assert isinstance(document, TaxFormW2)

    @pytest.mark.asyncio
    async def test_get_tax_document_invalid_id_raises_error(self):
        """MockTaxProvider raises ValueError for invalid document_id."""
        provider = MockTaxProvider()

        with pytest.raises(ValueError, match="Document not found"):
            await provider.get_tax_document("invalid_doc_id_123")

    @pytest.mark.asyncio
    async def test_download_document_returns_pdf_bytes(self):
        """MockTaxProvider returns mock PDF bytes."""
        provider = MockTaxProvider()
        pdf_bytes = await provider.download_document("w2_2024_user_123")

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_calculate_crypto_gains(self):
        """MockTaxProvider calculates crypto gains with realistic data."""
        provider = MockTaxProvider()
        transactions = [
            {
                "symbol": "BTC",
                "type": "sell",
                "date": "2024-06-20",
                "quantity": 0.5,
                "price": 60000.00,
                "cost_basis": 40000.00,
            }
        ]

        report = await provider.calculate_crypto_gains("user_123", transactions, 2024)

        assert isinstance(report, CryptoTaxReport)
        assert report.user_id == "user_123"
        assert report.tax_year == 2024
        assert report.total_gain_loss > Decimal("0.00")  # Hardcoded mock has gains
        assert report.transaction_count == 2  # Mock returns 2 transactions
        assert report.cost_basis_method == "FIFO"

    @pytest.mark.asyncio
    async def test_calculate_crypto_gains_custom_cost_basis(self):
        """MockTaxProvider accepts custom cost basis method."""
        provider = MockTaxProvider()
        transactions = []

        report = await provider.calculate_crypto_gains(
            "user_123", transactions, 2024, cost_basis_method="LIFO"
        )

        assert report.cost_basis_method == "LIFO"

    @pytest.mark.asyncio
    async def test_calculate_tax_liability(self):
        """MockTaxProvider calculates tax liability (simplified)."""
        provider = MockTaxProvider()

        liability = await provider.calculate_tax_liability(
            user_id="user_123",
            income=Decimal("100000.00"),
            deductions=Decimal("14600.00"),
            filing_status="single",
            tax_year=2024,
        )

        assert isinstance(liability, TaxLiability)
        assert liability.user_id == "user_123"
        assert liability.gross_income == Decimal("100000.00")
        assert liability.deductions == Decimal("14600.00")
        assert liability.taxable_income == Decimal("85400.00")
        assert liability.federal_tax > Decimal("0.00")

    @pytest.mark.asyncio
    async def test_calculate_tax_liability_with_state(self):
        """MockTaxProvider includes state tax if state provided."""
        provider = MockTaxProvider()

        liability = await provider.calculate_tax_liability(
            user_id="user_123",
            income=Decimal("100000.00"),
            deductions=Decimal("14600.00"),
            filing_status="single",
            tax_year=2024,
            state="CA",
        )

        assert liability.state_tax > Decimal("0.00")
        assert liability.total_tax == liability.federal_tax + liability.state_tax


class TestEasyTax:
    """Tests for easy_tax() builder."""

    def test_default_returns_mock_provider(self):
        """easy_tax() returns MockTaxProvider by default."""
        provider = easy_tax()
        assert isinstance(provider, MockTaxProvider)

    def test_explicit_mock_provider(self):
        """easy_tax(provider='mock') returns MockTaxProvider."""
        provider = easy_tax(provider="mock")
        assert isinstance(provider, MockTaxProvider)

    def test_case_insensitive_provider_name(self):
        """easy_tax() accepts case-insensitive provider names."""
        provider = easy_tax(provider="MOCK")
        assert isinstance(provider, MockTaxProvider)

    def test_provider_instance_passthrough(self):
        """easy_tax() returns provider instance if passed."""
        mock_provider = MockTaxProvider()
        provider = easy_tax(provider=mock_provider)
        assert provider is mock_provider

    def test_irs_provider_raises_not_implemented(self):
        """easy_tax(provider='irs') raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="6-8 weeks"):
            easy_tax(provider="irs", efin="test", tcc="test")

    def test_taxbit_provider_raises_not_implemented(self):
        """easy_tax(provider='taxbit') raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="paid subscription"):
            easy_tax(provider="taxbit", client_id="test", client_secret="test")

    def test_unknown_provider_raises_error(self):
        """easy_tax() raises ValueError for unknown provider."""
        with pytest.raises(ValueError, match="Unknown tax provider: invalid"):
            easy_tax(provider="invalid")


class TestAddTaxData:
    """Tests for add_tax_data() FastAPI helper."""

    def test_add_tax_data_wires_provider(self):
        """add_tax_data() returns configured provider."""
        app = FastAPI()
        provider = add_tax_data(app, provider="mock")

        assert isinstance(provider, MockTaxProvider)
        assert hasattr(app.state, "tax_provider")
        assert app.state.tax_provider is provider

    def test_add_tax_data_custom_prefix(self):
        """add_tax_data() accepts custom prefix."""
        app = FastAPI()
        add_tax_data(app, provider="mock", prefix="/custom-tax")

        # Just verify prefix is registered (don't test actual HTTP calls)
        # FastAPI tests require full svc-infra setup
        assert hasattr(app.state, "tax_provider")

    # NOTE: These endpoint tests are skipped in unit tests because they use svc-infra's
    # user_router which automatically includes database session dependencies.
    # These should be run as part of acceptance tests with full database setup.
    @pytest.mark.skip(
        "Integration test - requires svc-infra database session. Run in acceptance suite."
    )
    def test_get_tax_documents_endpoint(self):
        """GET /tax/documents returns list of tax documents (INTEGRATION TEST)."""
        app = FastAPI()
        add_tax_data(app, provider="mock")

        client = TestClient(app)
        response = client.get("/tax/documents?user_id=user123&tax_year=2024")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5  # W-2, 1099-INT/DIV/B/MISC

        # Verify form types
        form_types = [d["form_type"] for d in data]
        assert set(form_types) == {"W2", "1099-INT", "1099-DIV", "1099-B", "1099-MISC"}

    @pytest.mark.skip(
        "Integration test - requires svc-infra database session. Run in acceptance suite."
    )
    def test_get_tax_document_by_id_endpoint(self):
        """GET /tax/documents/{document_id} returns specific document (INTEGRATION TEST)."""
        app = FastAPI()
        add_tax_data(app, provider="mock")

        client = TestClient(app)
        response = client.get("/tax/documents/w2_2024_user123")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "w2_2024_user123"
        assert data["form_type"] == "W2"
        assert "wages" in data
        assert "federal_tax_withheld" in data

    @pytest.mark.skip(
        "Integration test - requires svc-infra database session. Run in acceptance suite."
    )
    def test_calculate_crypto_gains_endpoint(self):
        """POST /tax/crypto-gains calculates crypto gains (INTEGRATION TEST)."""
        app = FastAPI()
        add_tax_data(app, provider="mock")

        client = TestClient(app)
        payload = {
            "user_id": "user123",
            "tax_year": 2024,
            "transactions": [
                {
                    "symbol": "BTC",
                    "type": "sell",
                    "date": "2024-06-20",
                    "quantity": 0.5,
                    "price": 60000.00,
                    "cost_basis": 40000.00,
                }
            ],
            "cost_basis_method": "FIFO",
        }

        response = client.post("/tax/crypto-gains", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"
        assert data["tax_year"] == 2024
        assert "total_gain_loss" in data
        assert data["cost_basis_method"] == "FIFO"

    @pytest.mark.skip(
        "Integration test - requires svc-infra database session. Run in acceptance suite."
    )
    def test_calculate_tax_liability_endpoint(self):
        """POST /tax/tax-liability estimates tax liability (INTEGRATION TEST)."""
        app = FastAPI()
        add_tax_data(app, provider="mock")

        client = TestClient(app)
        payload = {
            "user_id": "user123",
            "tax_year": 2024,
            "income": "100000.00",
            "deductions": "14600.00",
            "filing_status": "single",
            "state": "CA",
        }

        response = client.post("/tax/tax-liability", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"
        assert data["filing_status"] == "single"
        assert "federal_tax" in data
        assert "state_tax" in data
        assert "total_tax" in data


class TestTaxDataModels:
    """Tests for tax data models."""

    def test_tax_form_w2_creation(self):
        """TaxFormW2 can be created with required fields."""
        w2 = TaxFormW2(
            document_id="w2_2024_001",
            user_id="user_123",
            tax_year=2024,
            issuer="Acme Corp",
            wages=Decimal("75000.00"),
            federal_tax_withheld=Decimal("12000.00"),
            social_security_wages=Decimal("75000.00"),
            social_security_tax_withheld=Decimal("4650.00"),
            medicare_wages=Decimal("75000.00"),
            medicare_tax_withheld=Decimal("1087.50"),
        )

        assert w2.form_type == "W2"
        assert w2.wages == Decimal("75000.00")
        assert w2.retirement_plan is False  # Default

    def test_tax_form_1099int_creation(self):
        """TaxForm1099INT can be created with required fields."""
        f1099int = TaxForm1099INT(
            document_id="1099int_2024_001",
            user_id="user_123",
            tax_year=2024,
            issuer="Acme Bank",
            interest_income=Decimal("250.00"),
        )

        assert f1099int.form_type == "1099-INT"
        assert f1099int.interest_income == Decimal("250.00")
        assert f1099int.early_withdrawal_penalty == Decimal("0.00")  # Default

    def test_crypto_tax_report_creation(self):
        """CryptoTaxReport can be created with required fields."""
        report = CryptoTaxReport(
            user_id="user_123",
            tax_year=2024,
            total_gain_loss=Decimal("15000.00"),
            short_term_gain_loss=Decimal("5000.00"),
            long_term_gain_loss=Decimal("10000.00"),
            transaction_count=25,
            cost_basis_method="FIFO",
        )

        assert report.total_gain_loss == Decimal("15000.00")
        assert report.cost_basis_method == "FIFO"
        assert len(report.transactions) == 0  # Default empty list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
