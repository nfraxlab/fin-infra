"""Response parsers for Experian API data to fin_infra models.

Converts Experian API JSON responses to typed Pydantic models:
- parse_credit_score(): dict → CreditScore
- parse_credit_report(): dict → CreditReport
- parse_account(): dict → CreditAccount
- parse_inquiry(): dict → CreditInquiry
- parse_public_record(): dict → PublicRecord

Example:
    >>> data = await client.get_credit_score("user123")
    >>> score = parse_credit_score(data, user_id="user123")
    >>> print(score.score)  # 735
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fin_infra.models.credit import (
    CreditAccount,
    CreditInquiry,
    CreditReport,
    CreditScore,
    PublicRecord,
)


def _parse_date(value: str | None) -> date | None:
    """Parse ISO date string to date object.

    Args:
        value: ISO date string (YYYY-MM-DD) or None

    Returns:
        date object or None
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, AttributeError):
        return None


def _parse_decimal(value: str | int | float | None) -> Decimal | None:
    """Parse numeric value to Decimal.

    Args:
        value: Numeric value (string, int, float) or None

    Returns:
        Decimal object or None
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return None


def parse_credit_score(data: dict[str, Any], *, user_id: str) -> CreditScore:
    """Parse Experian credit score response to CreditScore model.

    Expected Experian API response:
    {
      "creditProfile": {
        "score": 735,
        "scoreModel": "FICO 8",
        "scoreFactor": ["High utilization", "No late payments"],
        "scoreDate": "2025-11-06",
        "scoreChange": 15
      }
    }

    Args:
        data: Experian API response dict
        user_id: User identifier

    Returns:
        CreditScore Pydantic model

    Example:
        >>> data = {"creditProfile": {"score": 735, "scoreModel": "FICO 8", ...}}
        >>> score = parse_credit_score(data, user_id="user123")
        >>> print(score.score)  # 735
    """
    profile = data.get("creditProfile", {})

    return CreditScore(
        user_id=user_id,
        score=profile.get("score") or 300,  # Default to minimum valid score
        score_model=profile.get("scoreModel", "Unknown"),
        bureau="experian",
        score_date=_parse_date(profile.get("scoreDate")) or date.today(),
        factors=profile.get("scoreFactor", []),
        change=profile.get("scoreChange"),
    )


def parse_account(account_data: dict[str, Any]) -> CreditAccount:
    """Parse Experian tradeline (credit account) to CreditAccount model.

    Expected Experian tradeline format:
    {
      "accountId": "acc_123",
      "accountType": "credit_card",
      "creditorName": "Chase Bank",
      "accountStatus": "open",
      "currentBalance": "3500.00",
      "creditLimit": "10000.00",
      "paymentStatus": "current",
      "dateOpened": "2018-03-15",
      "lastPaymentDate": "2025-01-01",
      "monthlyPayment": "150.00"
    }

    Args:
        account_data: Experian tradeline dict

    Returns:
        CreditAccount Pydantic model
    """
    return CreditAccount(
        account_id=account_data.get("accountId", "unknown"),
        account_type=account_data.get("accountType", "other"),
        creditor_name=account_data.get("creditorName", "Unknown"),
        account_status=account_data.get("accountStatus", "open"),  # Default to "open"
        balance=_parse_decimal(account_data.get("currentBalance")) or Decimal("0"),
        credit_limit=_parse_decimal(account_data.get("creditLimit")),
        payment_status=account_data.get("paymentStatus", "current"),  # Default to "current"
        opened_date=_parse_date(account_data.get("dateOpened")) or date.today(),
        last_payment_date=_parse_date(account_data.get("lastPaymentDate")),
        monthly_payment=_parse_decimal(account_data.get("monthlyPayment")),
    )


def parse_inquiry(inquiry_data: dict[str, Any]) -> CreditInquiry:
    """Parse Experian inquiry to CreditInquiry model.

    Expected Experian inquiry format:
    {
      "inquiryId": "inq_123",
      "inquiryType": "hard",
      "inquirerName": "Chase Bank",
      "inquiryDate": "2025-01-01",
      "purpose": "credit_card_application"
    }

    Args:
        inquiry_data: Experian inquiry dict

    Returns:
        CreditInquiry Pydantic model
    """
    return CreditInquiry(
        inquiry_id=inquiry_data.get("inquiryId", "unknown"),
        inquiry_type=inquiry_data.get("inquiryType", "soft"),  # Default to "soft"
        inquirer_name=inquiry_data.get("inquirerName", "Unknown"),
        inquiry_date=_parse_date(inquiry_data.get("inquiryDate")) or date.today(),
        purpose=inquiry_data.get("purpose"),
    )


def parse_public_record(record_data: dict[str, Any]) -> PublicRecord:
    """Parse Experian public record to PublicRecord model.

    Expected Experian public record format:
    {
      "recordId": "rec_123",
      "recordType": "bankruptcy",
      "filingDate": "2020-01-01",
      "status": "discharged",
      "amount": "50000.00",
      "courtName": "U.S. Bankruptcy Court"
    }

    Args:
        record_data: Experian public record dict

    Returns:
        PublicRecord Pydantic model
    """
    return PublicRecord(
        record_id=record_data.get("recordId", "unknown"),
        record_type=record_data.get("recordType", "other"),
        filed_date=_parse_date(record_data.get("filingDate")) or date.today(),
        status=record_data.get("status", "active"),  # Default to "active"
        amount=_parse_decimal(record_data.get("amount")),
        court=record_data.get("courtName"),
    )


def parse_credit_report(data: dict[str, Any], *, user_id: str) -> CreditReport:
    """Parse Experian full credit report to CreditReport model.

    Expected Experian API response:
    {
      "creditProfile": {
        "score": {...},
        "tradelines": [...],
        "inquiries": [...],
        "publicRecords": [...],
        "consumerStatements": [...]
      }
    }

    Args:
        data: Experian API response dict
        user_id: User identifier

    Returns:
        CreditReport Pydantic model with all credit data

    Example:
        >>> data = await client.get_credit_report("user123")
        >>> report = parse_credit_report(data, user_id="user123")
        >>> print(len(report.accounts))  # Number of credit accounts
    """
    profile = data.get("creditProfile", {})

    # Parse credit score
    score = parse_credit_score(data, user_id=user_id)

    # Parse accounts (tradelines)
    accounts = [parse_account(acc) for acc in profile.get("tradelines", [])]

    # Parse inquiries
    inquiries = [parse_inquiry(inq) for inq in profile.get("inquiries", [])]

    # Parse public records
    public_records = [parse_public_record(rec) for rec in profile.get("publicRecords", [])]

    # Consumer statements (free-text explanations from user)
    consumer_statements = profile.get("consumerStatements", [])

    return CreditReport(
        user_id=user_id,
        bureau="experian",
        report_date=date.today(),
        score=score,
        accounts=accounts,
        inquiries=inquiries,
        public_records=public_records,
        consumer_statements=consumer_statements,
    )
