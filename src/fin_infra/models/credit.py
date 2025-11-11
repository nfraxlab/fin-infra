"""Credit score and credit report data models.

Models for credit bureau data (Experian, Equifax, TransUnion):
- CreditScore: Credit score with metadata
- CreditReport: Full credit report with accounts, inquiries, public records
- CreditAccount: Tradeline (credit card, loan, mortgage)
- CreditInquiry: Hard/soft credit inquiry
- PublicRecord: Bankruptcy, tax lien, judgment

PII Classification (see ADR-0011):
- Tier 1 (High-sensitivity): credit_score, account_number, SSN (if present)
- Tier 2 (Moderate): account balances, payment history, inquiries
- Tier 3 (Public): score model, bureau name, account types

FCRA Compliance:
- All credit data access must have permissible purpose
- Log all credit report accesses (see compliance.py)
- Provide adverse action notices if applicable
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreditScore(BaseModel):
    """Credit score from a bureau.

    Attributes:
        user_id: User identifier
        score: Credit score (300-850 for FICO, 300-850 for VantageScore)
        score_model: Scoring model - "FICO 8", "VantageScore 3.0", etc.
        bureau: Credit bureau - "experian", "equifax", "transunion"
        score_date: Date score was calculated
        factors: List of factors affecting score (positive/negative)
        change: Change since last pull (+/- points), None if first pull

    Example:
        >>> score = CreditScore(
        ...     user_id="user123",
        ...     score=735,
        ...     score_model="FICO 8",
        ...     bureau="experian",
        ...     score_date=date.today(),
        ...     factors=["Credit card utilization is high", "No recent late payments"],
        ...     change=+15
        ... )
    """

    user_id: str = Field(..., description="User identifier")
    score: int = Field(..., ge=300, le=850, description="Credit score (300-850)")  # PII: score
    score_model: str = Field(..., description="Scoring model (FICO 8, VantageScore 3.0, etc.)")
    bureau: Literal["experian", "equifax", "transunion"] = Field(..., description="Credit bureau")
    score_date: date = Field(..., description="Date score was calculated")
    factors: list[str] = Field(default_factory=list, description="Factors affecting score")
    change: int | None = Field(None, description="Change since last pull (+/- points)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "score": 735,
                "score_model": "FICO 8",
                "bureau": "experian",
                "score_date": "2025-01-15",
                "factors": [
                    "Credit card utilization is high (35%)",
                    "No recent late payments",
                    "Average age of accounts is good (8 years)",
                ],
                "change": 15,
            }
        }
    )


class CreditAccount(BaseModel):
    """Credit account (tradeline) from credit report.

    Attributes:
        account_id: Unique account identifier
        account_type: Type of account
        creditor_name: Name of creditor/lender
        account_status: Account status
        balance: Current balance
        credit_limit: Credit limit (for revolving accounts)
        payment_status: Payment status
        opened_date: Date account was opened
        last_payment_date: Date of last payment
        monthly_payment: Monthly payment amount (for installment loans)

    Example:
        >>> account = CreditAccount(
        ...     account_id="acc123",
        ...     account_type="credit_card",
        ...     creditor_name="Chase Bank",
        ...     account_status="open",
        ...     balance=Decimal("5000.00"),
        ...     credit_limit=Decimal("10000.00"),
        ...     payment_status="current",
        ...     opened_date=date(2020, 1, 1),
        ...     last_payment_date=date(2025, 1, 1),
        ... )
    """

    account_id: str = Field(..., description="Unique account identifier")
    account_type: Literal[
        "credit_card", "mortgage", "auto_loan", "student_loan", "personal_loan", "other"
    ] = Field(..., description="Type of account")
    creditor_name: str = Field(..., description="Name of creditor/lender")
    account_status: Literal["open", "closed", "charged_off", "collection"] = Field(
        ..., description="Account status"
    )
    balance: Decimal = Field(..., description="Current balance")  # PII: balance (GLBA)
    credit_limit: Decimal | None = Field(None, description="Credit limit (revolving accounts)")
    payment_status: Literal[
        "current", "30_days_late", "60_days_late", "90_days_late", "120_days_late"
    ] = Field(..., description="Payment status")
    opened_date: date = Field(..., description="Date account was opened")
    last_payment_date: date | None = Field(None, description="Date of last payment")
    monthly_payment: Decimal | None = Field(None, description="Monthly payment amount")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "acc123",
                "account_type": "credit_card",
                "creditor_name": "Chase Bank",
                "account_status": "open",
                "balance": "5000.00",
                "credit_limit": "10000.00",
                "payment_status": "current",
                "opened_date": "2020-01-01",
                "last_payment_date": "2025-01-01",
                "monthly_payment": "150.00",
            }
        }
    )


class CreditInquiry(BaseModel):
    """Credit inquiry (hard/soft pull) from credit report.

    Attributes:
        inquiry_id: Unique inquiry identifier
        inquiry_type: Type of inquiry
        inquirer_name: Name of entity that pulled credit
        inquiry_date: Date of inquiry
        purpose: Purpose of inquiry (optional)

    Example:
        >>> inquiry = CreditInquiry(
        ...     inquiry_id="inq123",
        ...     inquiry_type="hard",
        ...     inquirer_name="Chase Bank",
        ...     inquiry_date=date(2025, 1, 1),
        ...     purpose="credit_card_application",
        ... )
    """

    inquiry_id: str = Field(..., description="Unique inquiry identifier")
    inquiry_type: Literal["hard", "soft"] = Field(..., description="Type of inquiry")
    inquirer_name: str = Field(..., description="Name of entity that pulled credit")
    inquiry_date: date = Field(..., description="Date of inquiry")
    purpose: (
        Literal[
            "credit_card_application",
            "mortgage",
            "auto_loan",
            "personal_loan",
            "employment_check",
            "account_review",
            "other",
        ]
        | None
    ) = Field(None, description="Purpose of inquiry")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inquiry_id": "inq123",
                "inquiry_type": "hard",
                "inquirer_name": "Chase Bank",
                "inquiry_date": "2025-01-01",
                "purpose": "credit_card_application",
            }
        }
    )


class PublicRecord(BaseModel):
    """Public record (bankruptcy, lien, judgment) from credit report.

    Attributes:
        record_id: Unique record identifier
        record_type: Type of public record
        filed_date: Date record was filed
        status: Status of record
        amount: Amount (if applicable)
        court: Court name (if applicable)

    Example:
        >>> record = PublicRecord(
        ...     record_id="rec123",
        ...     record_type="bankruptcy",
        ...     filed_date=date(2020, 1, 1),
        ...     status="discharged",
        ...     amount=Decimal("50000.00"),
        ...     court="U.S. Bankruptcy Court",
        ... )
    """

    record_id: str = Field(..., description="Unique record identifier")
    record_type: Literal["bankruptcy", "tax_lien", "judgment", "other"] = Field(
        ..., description="Type of public record"
    )
    filed_date: date = Field(..., description="Date record was filed")
    status: Literal["active", "satisfied", "discharged", "dismissed"] = Field(
        ..., description="Status of record"
    )
    amount: Decimal | None = Field(None, description="Amount (if applicable)")
    court: str | None = Field(None, description="Court name (if applicable)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "record_id": "rec123",
                "record_type": "bankruptcy",
                "filed_date": "2020-01-01",
                "status": "discharged",
                "amount": "50000.00",
                "court": "U.S. Bankruptcy Court",
            }
        }
    )


class CreditReport(BaseModel):
    """Full credit report from a bureau.

    Attributes:
        user_id: User identifier
        bureau: Credit bureau
        report_date: Date report was generated
        score: Credit score
        accounts: List of credit accounts (tradelines)
        inquiries: List of credit inquiries
        public_records: List of public records
        consumer_statements: List of consumer statements (disputes, etc.)

    Example:
        >>> report = CreditReport(
        ...     user_id="user123",
        ...     bureau="experian",
        ...     report_date=date.today(),
        ...     score=CreditScore(...),
        ...     accounts=[CreditAccount(...), ...],
        ...     inquiries=[CreditInquiry(...), ...],
        ...     public_records=[],
        ...     consumer_statements=["I dispute account #12345"],
        ... )
    """

    user_id: str = Field(..., description="User identifier")
    bureau: Literal["experian", "equifax", "transunion"] = Field(..., description="Credit bureau")
    report_date: date = Field(..., description="Date report was generated")
    score: CreditScore = Field(..., description="Credit score")
    accounts: list[CreditAccount] = Field(default_factory=list, description="Credit accounts")
    inquiries: list[CreditInquiry] = Field(default_factory=list, description="Credit inquiries")
    public_records: list[PublicRecord] = Field(default_factory=list, description="Public records")
    consumer_statements: list[str] = Field(
        default_factory=list, description="Consumer statements (disputes, etc.)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "bureau": "experian",
                "report_date": "2025-01-15",
                "score": {
                    "user_id": "user123",
                    "score": 735,
                    "score_model": "FICO 8",
                    "bureau": "experian",
                    "score_date": "2025-01-15",
                    "factors": ["Credit card utilization is high (35%)"],
                    "change": 15,
                },
                "accounts": [
                    {
                        "account_id": "acc123",
                        "account_type": "credit_card",
                        "creditor_name": "Chase Bank",
                        "account_status": "open",
                        "balance": "5000.00",
                        "credit_limit": "10000.00",
                        "payment_status": "current",
                        "opened_date": "2020-01-01",
                        "last_payment_date": "2025-01-01",
                    }
                ],
                "inquiries": [
                    {
                        "inquiry_id": "inq123",
                        "inquiry_type": "hard",
                        "inquirer_name": "Chase Bank",
                        "inquiry_date": "2025-01-01",
                        "purpose": "credit_card_application",
                    }
                ],
                "public_records": [],
                "consumer_statements": [],
            }
        }
    )


__all__ = [
    "CreditScore",
    "CreditAccount",
    "CreditInquiry",
    "PublicRecord",
    "CreditReport",
]
