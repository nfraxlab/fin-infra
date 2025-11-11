"""Unit tests for Experian response parser.

Tests:
- parse_credit_score() - Experian JSON → CreditScore model
- parse_credit_report() - Experian JSON → CreditReport model
- parse_account() - tradeline → CreditAccount
- parse_inquiry() - inquiry → CreditInquiry
- parse_public_record() - public record → PublicRecord
- Edge cases (missing fields, null values, invalid dates)

All tests use mock Experian API responses.
"""

from datetime import date
from decimal import Decimal


from fin_infra.credit.experian.parser import (
    _parse_date,
    _parse_decimal,
    parse_account,
    parse_credit_report,
    parse_credit_score,
    parse_inquiry,
    parse_public_record,
)
from fin_infra.models.credit import (
    CreditAccount,
    CreditInquiry,
    CreditReport,
    CreditScore,
    PublicRecord,
)


class TestParserHelpers:
    """Test parser helper functions."""

    def test_parse_date_valid_iso_string(self):
        """Test _parse_date parses valid ISO date string."""
        result = _parse_date("2025-11-06")
        assert result == date(2025, 11, 6)

    def test_parse_date_none(self):
        """Test _parse_date returns None for None input."""
        result = _parse_date(None)
        assert result is None

    def test_parse_date_invalid_string(self):
        """Test _parse_date returns None for invalid date string."""
        result = _parse_date("invalid-date")
        assert result is None

    def test_parse_date_empty_string(self):
        """Test _parse_date returns None for empty string."""
        result = _parse_date("")
        assert result is None

    def test_parse_decimal_valid_string(self):
        """Test _parse_decimal parses valid numeric string."""
        result = _parse_decimal("3500.50")
        assert result == Decimal("3500.50")

    def test_parse_decimal_integer(self):
        """Test _parse_decimal parses integer."""
        result = _parse_decimal(1000)
        assert result == Decimal("1000")

    def test_parse_decimal_float(self):
        """Test _parse_decimal parses float."""
        result = _parse_decimal(1000.99)
        assert result == Decimal("1000.99")

    def test_parse_decimal_none(self):
        """Test _parse_decimal returns None for None input."""
        result = _parse_decimal(None)
        assert result is None

    def test_parse_decimal_invalid_string(self):
        """Test _parse_decimal returns None for invalid string."""
        result = _parse_decimal("invalid")
        assert result is None


class TestParseCreditScore:
    """Test parse_credit_score function."""

    def test_parse_credit_score_complete_data(self):
        """Test parse_credit_score with complete Experian response."""
        data = {
            "creditProfile": {
                "score": 750,
                "scoreModel": "FICO 8",
                "scoreFactor": [
                    "Credit card utilization is high",
                    "No recent late payments",
                ],
                "scoreDate": "2025-11-06",
                "scoreChange": 15,
            }
        }

        result = parse_credit_score(data, user_id="user123")

        assert isinstance(result, CreditScore)
        assert result.user_id == "user123"
        assert result.score == 750
        assert result.score_model == "FICO 8"
        assert result.bureau == "experian"
        assert result.score_date == date(2025, 11, 6)
        assert len(result.factors) == 2
        assert result.change == 15

    def test_parse_credit_score_missing_optional_fields(self):
        """Test parse_credit_score handles missing optional fields."""
        data = {
            "creditProfile": {
                "score": 700,
                # Missing scoreModel, scoreFactor, scoreDate, scoreChange
            }
        }

        result = parse_credit_score(data, user_id="user123")

        assert result.score == 700
        assert result.score_model == "Unknown"  # Default
        assert result.factors == []  # Default
        assert result.change is None
        assert result.score_date == date.today()  # Default

    def test_parse_credit_score_empty_credit_profile(self):
        """Test parse_credit_score handles empty creditProfile."""
        data = {"creditProfile": {}}

        result = parse_credit_score(data, user_id="user123")

        assert result.score == 300  # Default to minimum valid score
        assert result.score_model == "Unknown"
        assert result.bureau == "experian"
        assert result.score_date == date.today()
        assert result.factors == []

    def test_parse_credit_score_missing_credit_profile(self):
        """Test parse_credit_score handles missing creditProfile key."""
        data = {}

        result = parse_credit_score(data, user_id="user123")

        assert result.score == 300  # Default to minimum valid score
        assert result.score_model == "Unknown"


class TestParseAccount:
    """Test parse_account function."""

    def test_parse_account_complete_data(self):
        """Test parse_account with complete tradeline data."""
        account_data = {
            "accountId": "acc_123",
            "accountType": "credit_card",
            "creditorName": "Chase Bank",
            "accountStatus": "open",
            "currentBalance": "3500.00",
            "creditLimit": "10000.00",
            "paymentStatus": "current",
            "dateOpened": "2018-03-15",
            "lastPaymentDate": "2025-11-01",
            "monthlyPayment": "150.00",
        }

        result = parse_account(account_data)

        assert isinstance(result, CreditAccount)
        assert result.account_id == "acc_123"
        assert result.account_type == "credit_card"
        assert result.creditor_name == "Chase Bank"
        assert result.account_status == "open"
        assert result.balance == Decimal("3500.00")
        assert result.credit_limit == Decimal("10000.00")
        assert result.payment_status == "current"
        assert result.opened_date == date(2018, 3, 15)
        assert result.last_payment_date == date(2025, 11, 1)
        assert result.monthly_payment == Decimal("150.00")

    def test_parse_account_missing_optional_fields(self):
        """Test parse_account handles missing optional fields."""
        account_data = {
            "accountId": "acc_456",
            "accountType": "auto_loan",
            # Missing most fields
        }

        result = parse_account(account_data)

        assert result.account_id == "acc_456"
        assert result.account_type == "auto_loan"
        assert result.creditor_name == "Unknown"  # Default
        assert result.balance == Decimal("0")  # Default
        assert result.credit_limit is None
        assert result.account_status == "open"  # Default
        assert result.payment_status == "current"  # Default
        assert result.opened_date == date.today()  # Default

    def test_parse_account_null_credit_limit(self):
        """Test parse_account handles null credit limit (e.g., loans)."""
        account_data = {
            "accountId": "acc_loan",
            "accountType": "student_loan",
            "currentBalance": "25000.00",
            "creditLimit": None,  # Loans don't have credit limits
        }

        result = parse_account(account_data)

        assert result.balance == Decimal("25000.00")
        assert result.credit_limit is None


class TestParseInquiry:
    """Test parse_inquiry function."""

    def test_parse_inquiry_complete_data(self):
        """Test parse_inquiry with complete inquiry data."""
        inquiry_data = {
            "inquiryId": "inq_123",
            "inquiryType": "hard",
            "inquirerName": "Chase Bank",
            "inquiryDate": "2025-01-15",
            "purpose": "credit_card_application",
        }

        result = parse_inquiry(inquiry_data)

        assert isinstance(result, CreditInquiry)
        assert result.inquiry_id == "inq_123"
        assert result.inquiry_type == "hard"
        assert result.inquirer_name == "Chase Bank"
        assert result.inquiry_date == date(2025, 1, 15)
        assert result.purpose == "credit_card_application"

    def test_parse_inquiry_missing_optional_fields(self):
        """Test parse_inquiry handles missing optional fields."""
        inquiry_data = {
            "inquiryId": "inq_456",
            # Missing most fields
        }

        result = parse_inquiry(inquiry_data)

        assert result.inquiry_id == "inq_456"
        assert result.inquiry_type == "soft"  # Default
        assert result.inquirer_name == "Unknown"
        assert result.inquiry_date == date.today()
        assert result.purpose is None

    def test_parse_inquiry_soft_inquiry(self):
        """Test parse_inquiry handles soft inquiry type."""
        inquiry_data = {
            "inquiryId": "inq_soft",
            "inquiryType": "soft",
            "inquirerName": "Pre-approval Check",
            "inquiryDate": "2025-10-01",
        }

        result = parse_inquiry(inquiry_data)

        assert result.inquiry_type == "soft"


class TestParsePublicRecord:
    """Test parse_public_record function."""

    def test_parse_public_record_complete_data(self):
        """Test parse_public_record with complete data."""
        record_data = {
            "recordId": "rec_123",
            "recordType": "bankruptcy",
            "filingDate": "2020-01-15",
            "status": "discharged",
            "amount": "50000.00",
            "courtName": "U.S. Bankruptcy Court",
        }

        result = parse_public_record(record_data)

        assert isinstance(result, PublicRecord)
        assert result.record_id == "rec_123"
        assert result.record_type == "bankruptcy"
        assert result.filed_date == date(2020, 1, 15)  # Note: field is filed_date not filing_date
        assert result.status == "discharged"
        assert result.amount == Decimal("50000.00")
        assert result.court == "U.S. Bankruptcy Court"

    def test_parse_public_record_missing_optional_fields(self):
        """Test parse_public_record handles missing optional fields."""
        record_data = {
            "recordId": "rec_456",
            "recordType": "tax_lien",
            # Missing most fields
        }

        result = parse_public_record(record_data)

        assert result.record_id == "rec_456"
        assert result.record_type == "tax_lien"
        assert result.filed_date == date.today()  # Default (field is filed_date not filing_date)
        assert result.status == "active"  # Default
        assert result.amount is None
        assert result.court is None

    def test_parse_public_record_missing_optional_fields(self):
        """Test parse_public_record handles missing optional fields."""
        record_data = {
            "recordId": "rec_456",
            "recordType": "tax_lien",
            # Missing most fields
        }

        result = parse_public_record(record_data)

        assert result.record_id == "rec_456"
        assert result.record_type == "tax_lien"
        assert result.filed_date == date.today()  # Default (field is filed_date not filing_date)
        assert result.status == "active"  # Default
        assert result.amount is None
        assert result.court is None


class TestParseCreditReport:
    """Test parse_credit_report function."""

    def test_parse_credit_report_complete_data(self):
        """Test parse_credit_report with complete Experian response."""
        data = {
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
                    },
                    {
                        "accountId": "acc_2",
                        "accountType": "auto_loan",
                        "creditorName": "Ford Credit",
                        "accountStatus": "open",
                        "currentBalance": "15000.00",
                    },
                ],
                "inquiries": [
                    {
                        "inquiryId": "inq_1",
                        "inquiryType": "hard",
                        "inquirerName": "Chase",
                        "inquiryDate": "2025-01-01",
                    }
                ],
                "publicRecords": [
                    {
                        "recordId": "rec_1",
                        "recordType": "bankruptcy",
                        "filingDate": "2019-01-01",
                        "status": "discharged",
                    }
                ],
                "consumerStatements": ["I was a victim of identity theft"],
            }
        }

        result = parse_credit_report(data, user_id="user123")

        assert isinstance(result, CreditReport)
        assert result.user_id == "user123"
        assert result.bureau == "experian"
        assert result.report_date == date.today()

        # Check score
        assert result.score.score == 750
        assert result.score.score_model == "FICO 8"

        # Check accounts
        assert len(result.accounts) == 2
        assert result.accounts[0].account_id == "acc_1"
        assert result.accounts[1].account_id == "acc_2"

        # Check inquiries
        assert len(result.inquiries) == 1
        assert result.inquiries[0].inquiry_id == "inq_1"

        # Check public records
        assert len(result.public_records) == 1
        assert result.public_records[0].record_id == "rec_1"

        # Check consumer statements
        assert len(result.consumer_statements) == 1
        assert result.consumer_statements[0] == "I was a victim of identity theft"

    def test_parse_credit_report_empty_arrays(self):
        """Test parse_credit_report handles empty arrays."""
        data = {
            "creditProfile": {
                "score": 700,
                "tradelines": [],
                "inquiries": [],
                "publicRecords": [],
                "consumerStatements": [],
            }
        }

        result = parse_credit_report(data, user_id="user123")

        assert len(result.accounts) == 0
        assert len(result.inquiries) == 0
        assert len(result.public_records) == 0
        assert len(result.consumer_statements) == 0

    def test_parse_credit_report_missing_arrays(self):
        """Test parse_credit_report handles missing array fields."""
        data = {
            "creditProfile": {
                "score": 700,
                # Missing tradelines, inquiries, etc.
            }
        }

        result = parse_credit_report(data, user_id="user123")

        assert len(result.accounts) == 0  # Default empty list
        assert len(result.inquiries) == 0
        assert len(result.public_records) == 0
        assert len(result.consumer_statements) == 0

    def test_parse_credit_report_multiple_accounts(self):
        """Test parse_credit_report correctly parses multiple accounts."""
        data = {
            "creditProfile": {
                "score": 750,
                "tradelines": [
                    {"accountId": f"acc_{i}", "accountType": "credit_card"} for i in range(5)
                ],
            }
        }

        result = parse_credit_report(data, user_id="user123")

        assert len(result.accounts) == 5
        assert all(acc.account_type == "credit_card" for acc in result.accounts)
