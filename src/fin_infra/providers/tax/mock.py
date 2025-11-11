"""Mock tax provider for development and testing.

Provides hardcoded tax documents and crypto tax calculations.
No external API calls required.

Example:
    >>> from fin_infra.providers.tax.mock import MockTaxProvider
    >>> provider = MockTaxProvider()
    >>> documents = await provider.get_tax_documents("user_123", 2024)
    >>> print(len(documents))  # 3 (W-2, 1099-INT, 1099-DIV)
"""

from datetime import date, datetime
from decimal import Decimal

from fin_infra.models.tax import (
    TaxDocument,
    TaxFormW2,
    TaxForm1099INT,
    TaxForm1099DIV,
    TaxForm1099B,
    TaxForm1099MISC,
    CryptoTransaction,
    CryptoTaxReport,
    TaxLiability,
)
from fin_infra.providers.base import TaxProvider


class MockTaxProvider(TaxProvider):
    """Mock tax provider with hardcoded sample data.

    Returns realistic tax documents for testing.
    No API keys or external dependencies required.

    Supported forms:
        - W-2: Wage and Tax Statement
        - 1099-INT: Interest Income
        - 1099-DIV: Dividends and Distributions
        - 1099-B: Broker Transactions (crypto/stocks)
        - 1099-MISC: Miscellaneous Income (staking)

    Example:
        >>> provider = MockTaxProvider()
        >>> documents = await provider.get_tax_documents("user_123", 2024)
        >>> w2 = [d for d in documents if d.form_type == "W2"][0]
        >>> print(w2.wages)  # 75000.00
    """

    def __init__(self, **kwargs):
        """Initialize mock provider (no configuration needed)."""
        pass

    async def get_tax_forms(self, user_id: str, tax_year: int, **kwargs) -> list[dict]:
        """Retrieve tax forms for a user and tax year (returns dict, not models).

        This method satisfies the TaxProvider ABC interface.
        Use get_tax_documents() for typed models instead.

        Args:
            user_id: User identifier
            tax_year: Tax year (e.g., 2024)
            **kwargs: Additional parameters (ignored)

        Returns:
            List of tax forms as dicts
        """
        # Get typed documents
        documents = await self.get_tax_documents(user_id, tax_year)

        # Convert to dicts
        return [doc.model_dump() for doc in documents]

    async def get_tax_documents(self, user_id: str, tax_year: int, **kwargs) -> list[TaxDocument]:
        """Retrieve all tax documents for a user and tax year.

        Returns hardcoded W-2, 1099-INT, 1099-DIV, 1099-B, 1099-MISC.

        Args:
            user_id: User identifier
            tax_year: Tax year (e.g., 2024)
            **kwargs: Additional parameters (ignored)

        Returns:
            List of tax documents (5 forms)

        Example:
            >>> provider = MockTaxProvider()
            >>> docs = await provider.get_tax_documents("user_123", 2024)
            >>> print(len(docs))  # 5
            >>> print([d.form_type for d in docs])
            # ['W2', '1099-INT', '1099-DIV', '1099-B', '1099-MISC']
        """
        documents: list[TaxDocument] = [
            # W-2: Employment income
            TaxFormW2(
                document_id=f"w2_{tax_year}_{user_id}",
                user_id=user_id,
                tax_year=tax_year,
                issuer="Acme Corporation",
                issuer_ein="12-3456789",
                wages=Decimal("75000.00"),
                federal_tax_withheld=Decimal("12000.00"),
                social_security_wages=Decimal("75000.00"),
                social_security_tax_withheld=Decimal("4650.00"),
                medicare_wages=Decimal("75000.00"),
                medicare_tax_withheld=Decimal("1087.50"),
                box_12_codes={"D": Decimal("5000.00")},  # 401k contributions
                retirement_plan=True,
                state_wages=Decimal("75000.00"),
                state_tax_withheld=Decimal("3750.00"),
                state="CA",
                status="available",
                created_at=datetime(tax_year, 1, 31, 10, 0, 0),
                updated_at=datetime(tax_year, 1, 31, 10, 0, 0),
            ),
            # 1099-INT: Interest income from savings
            TaxForm1099INT(
                document_id=f"1099int_{tax_year}_{user_id}",
                user_id=user_id,
                tax_year=tax_year,
                issuer="Acme Bank",
                issuer_ein="98-7654321",
                interest_income=Decimal("250.00"),
                early_withdrawal_penalty=Decimal("0.00"),
                us_savings_bonds_interest=Decimal("0.00"),
                federal_tax_withheld=Decimal("0.00"),
                tax_exempt_interest=Decimal("0.00"),
                status="available",
                created_at=datetime(tax_year, 1, 31, 10, 0, 0),
                updated_at=datetime(tax_year, 1, 31, 10, 0, 0),
            ),
            # 1099-DIV: Dividend income from investments
            TaxForm1099DIV(
                document_id=f"1099div_{tax_year}_{user_id}",
                user_id=user_id,
                tax_year=tax_year,
                issuer="Vanguard",
                issuer_ein="23-1234567",
                ordinary_dividends=Decimal("500.00"),
                qualified_dividends=Decimal("400.00"),
                capital_gain_distributions=Decimal("100.00"),
                nondividend_distributions=Decimal("0.00"),
                federal_tax_withheld=Decimal("0.00"),
                status="available",
                created_at=datetime(tax_year, 1, 31, 10, 0, 0),
                updated_at=datetime(tax_year, 1, 31, 10, 0, 0),
            ),
            # 1099-B: Crypto sale (long-term gain)
            TaxForm1099B(
                document_id=f"1099b_{tax_year}_{user_id}",
                user_id=user_id,
                tax_year=tax_year,
                issuer="Coinbase",
                issuer_ein="45-6789012",
                description="0.5 BTC",
                date_acquired=date(tax_year - 2, 3, 15),
                date_sold=date(tax_year, 6, 20),
                proceeds=Decimal("30000.00"),
                cost_basis=Decimal("20000.00"),
                gain_or_loss=Decimal("10000.00"),
                holding_period="long_term",
                federal_tax_withheld=Decimal("0.00"),
                status="available",
                created_at=datetime(tax_year, 1, 31, 10, 0, 0),
                updated_at=datetime(tax_year, 1, 31, 10, 0, 0),
            ),
            # 1099-MISC: Staking rewards
            TaxForm1099MISC(
                document_id=f"1099misc_{tax_year}_{user_id}",
                user_id=user_id,
                tax_year=tax_year,
                issuer="Coinbase",
                issuer_ein="45-6789012",
                rents=Decimal("0.00"),
                royalties=Decimal("0.00"),
                other_income=Decimal("1200.00"),  # ETH staking rewards
                federal_tax_withheld=Decimal("0.00"),
                status="available",
                created_at=datetime(tax_year, 1, 31, 10, 0, 0),
                updated_at=datetime(tax_year, 1, 31, 10, 0, 0),
            ),
        ]

        return documents

    async def get_tax_document(self, document_id: str, **kwargs) -> TaxDocument:
        """Retrieve a specific tax document by ID.

        Args:
            document_id: Document identifier (e.g., "w2_2024_user_123")
            **kwargs: Additional parameters (ignored)

        Returns:
            Tax document matching the ID

        Raises:
            ValueError: If document_id not found

        Example:
            >>> provider = MockTaxProvider()
            >>> doc = await provider.get_tax_document("w2_2024_user_123")
            >>> print(doc.form_type)  # W2
        """
        # Parse document_id to extract form type, year, user_id
        # Format: "{form_type}_{tax_year}_{user_id}"
        parts = document_id.split("_")
        if len(parts) < 3:
            raise ValueError(f"Invalid document_id format: {document_id}")

        # For form types with hyphens (1099-INT, etc.), need special handling
        # Example: "1099int_2024_user_123" or "w2_2024_user_123"
        # We'll just get all documents and search by ID
        tax_year = int(parts[1]) if parts[1].isdigit() else 2024
        user_id = "_".join(parts[2:]) if len(parts) > 2 else "unknown"

        # Get all documents and filter by ID
        all_documents = await self.get_tax_documents(user_id, tax_year)
        matching = [d for d in all_documents if d.document_id == document_id]

        if not matching:
            raise ValueError(f"Document not found: {document_id}")

        return matching[0]

    async def download_document(self, document_id: str, **kwargs) -> bytes:
        """Download PDF bytes for a tax document.

        Args:
            document_id: Document identifier
            **kwargs: Additional parameters (ignored)

        Returns:
            PDF file bytes (mock: returns placeholder PDF)

        Example:
            >>> provider = MockTaxProvider()
            >>> pdf_bytes = await provider.download_document("w2_2024_user_123")
            >>> print(len(pdf_bytes) > 0)  # True
        """
        # Return minimal valid PDF (mock implementation)
        # In production, this would fetch from S3/GCS or generate on-the-fly
        return b"%PDF-1.4\n%Mock Tax Document PDF\n"

    async def calculate_crypto_gains(
        self, user_id: str, transactions: list[dict], tax_year: int, **kwargs
    ) -> CryptoTaxReport:
        """Calculate capital gains for crypto transactions.

        Args:
            user_id: User identifier
            transactions: List of crypto trades (dicts with symbol, date, quantity, price, etc.)
            tax_year: Tax year
            **kwargs: Additional parameters (cost_basis_method="FIFO", etc.)

        Returns:
            Crypto tax report with gains/losses breakdown

        Example:
            >>> provider = MockTaxProvider()
            >>> transactions = [
            ...     {"symbol": "BTC", "type": "sell", "date": "2024-06-20",
            ...      "quantity": 0.5, "price": 60000.00, "cost_basis": 40000.00}
            ... ]
            >>> report = await provider.calculate_crypto_gains("user_123", transactions, 2024)
            >>> print(report.total_gain_loss)  # 10000.00
        """
        # Mock calculation (in production, this would use FIFO/LIFO/HIFO)
        cost_basis_method = kwargs.get("cost_basis_method", "FIFO")

        # Hardcoded example report
        crypto_transactions = [
            CryptoTransaction(
                transaction_id="tx_001",
                symbol="BTC",
                transaction_type="sell",
                date=date(tax_year, 6, 20),
                quantity=Decimal("0.5"),
                price_per_unit=Decimal("60000.00"),
                total_value=Decimal("30000.00"),
                fees=Decimal("50.00"),
                cost_basis=Decimal("20000.00"),
                gain_or_loss=Decimal("9950.00"),  # 30000 - 20000 - 50
                holding_period="long_term",
            ),
            CryptoTransaction(
                transaction_id="tx_002",
                symbol="ETH",
                transaction_type="sell",
                date=date(tax_year, 12, 15),
                quantity=Decimal("2.0"),
                price_per_unit=Decimal("3000.00"),
                total_value=Decimal("6000.00"),
                fees=Decimal("20.00"),
                cost_basis=Decimal("4000.00"),
                gain_or_loss=Decimal("1980.00"),  # 6000 - 4000 - 20
                holding_period="short_term",
            ),
        ]

        # Calculate totals
        short_term = sum(
            tx.gain_or_loss
            for tx in crypto_transactions
            if tx.holding_period == "short_term" and tx.gain_or_loss
        )
        long_term = sum(
            tx.gain_or_loss
            for tx in crypto_transactions
            if tx.holding_period == "long_term" and tx.gain_or_loss
        )

        return CryptoTaxReport(
            user_id=user_id,
            tax_year=tax_year,
            total_gain_loss=short_term + long_term,
            short_term_gain_loss=short_term,
            long_term_gain_loss=long_term,
            transaction_count=len(crypto_transactions),
            cost_basis_method=cost_basis_method,
            transactions=crypto_transactions,
            form_8949_data=None,  # Would be generated by TaxBit in production
        )

    async def calculate_tax_liability(
        self,
        user_id: str,
        income: Decimal,
        deductions: Decimal,
        filing_status: str,
        tax_year: int,
        **kwargs,
    ) -> TaxLiability:
        """Estimate tax liability (basic calculation).

        Args:
            user_id: User identifier
            income: Gross income
            deductions: Standard or itemized deductions
            filing_status: "single", "married_joint", etc.
            tax_year: Tax year
            **kwargs: Additional parameters (state="CA", etc.)

        Returns:
            Tax liability estimate

        Example:
            >>> provider = MockTaxProvider()
            >>> liability = await provider.calculate_tax_liability(
            ...     "user_123",
            ...     Decimal("100000.00"),
            ...     Decimal("14600.00"),
            ...     "single",
            ...     2024
            ... )
            >>> print(liability.federal_tax)  # ~14296.00
        """
        # Simplified tax calculation (mock: uses flat 15% federal, 5% state)
        # In production, would use actual IRS tax brackets
        taxable_income = income - deductions
        federal_tax = taxable_income * Decimal("0.15")

        # State tax (if state provided)
        state = kwargs.get("state")
        state_tax = taxable_income * Decimal("0.05") if state else Decimal("0.00")

        total_tax = federal_tax + state_tax
        effective_rate = (total_tax / income * 100) if income > 0 else Decimal("0.00")

        return TaxLiability(
            user_id=user_id,
            tax_year=tax_year,
            filing_status=filing_status,
            gross_income=income,
            deductions=deductions,
            taxable_income=taxable_income,
            federal_tax=federal_tax,
            state_tax=state_tax,
            total_tax=total_tax,
            effective_tax_rate=effective_rate.quantize(Decimal("0.01")),
        )


__all__ = ["MockTaxProvider"]
