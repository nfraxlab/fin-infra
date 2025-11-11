"""
Tests for financial security module.

Tests PII masking, token encryption, and audit logging.
"""

import logging
import os

import pytest
from cryptography.fernet import Fernet

from fin_infra.security import (
    FinancialPIIFilter,
    ProviderTokenEncryption,
    add_financial_security,
    generate_encryption_key,
    log_pii_access,
    get_audit_logs,
    clear_audit_logs,
    luhn_checksum,
    is_valid_routing_number,
)


class TestPIIMasking:
    """Test PII detection and masking in logs."""

    def setup_method(self):
        """Setup logging with PII filter."""
        self.logger = logging.getLogger("test_pii")
        self.logger.setLevel(logging.INFO)

        # Add PII filter
        self.pii_filter = FinancialPIIFilter()
        self.logger.addFilter(self.pii_filter)

        # Add handler to capture log output
        self.log_records = []

        class ListHandler(logging.Handler):
            def __init__(self, log_records):
                super().__init__()
                self.log_records = log_records

            def emit(self, record):
                self.log_records.append(record)

        self.handler = ListHandler(self.log_records)
        self.logger.addHandler(self.handler)

    def teardown_method(self):
        """Remove handler."""
        self.logger.removeHandler(self.handler)
        self.logger.removeFilter(self.pii_filter)

    def test_mask_ssn_with_dashes(self):
        """Test SSN masking with dashes."""
        self.logger.info("Processing SSN: 123-45-6789")

        assert len(self.log_records) == 1
        assert "***-**-6789" in self.log_records[0].msg
        assert "123-45" not in self.log_records[0].msg

    def test_mask_ssn_without_dashes(self):
        """Test SSN masking without dashes (with context)."""
        self.logger.info("User SSN is 123456789")

        assert len(self.log_records) == 1
        assert "*****6789" in self.log_records[0].msg
        assert "123456789" not in self.log_records[0].msg

    def test_mask_account_number(self):
        """Test bank account number masking."""
        self.logger.info("Account number: 1234567890")

        assert len(self.log_records) == 1
        assert "******7890" in self.log_records[0].msg
        assert "1234567890" not in self.log_records[0].msg

    def test_mask_routing_number(self):
        """Test ABA routing number masking."""
        self.logger.info("Routing number 021000021")

        assert len(self.log_records) == 1
        assert "******021" in self.log_records[0].msg
        assert "021000021" not in self.log_records[0].msg

    def test_mask_credit_card(self):
        """Test credit card masking with Luhn validation."""
        # Valid Visa card
        self.logger.info("Card: 4111 1111 1111 1111")

        assert len(self.log_records) == 1
        assert "**** **** **** 1111" in self.log_records[0].msg
        assert "4111 1111 1111 1111" not in self.log_records[0].msg

    def test_mask_credit_card_no_spaces(self):
        """Test credit card masking without spaces."""
        self.logger.info("Card: 4111111111111111")

        assert len(self.log_records) == 1
        assert "************1111" in self.log_records[0].msg
        assert "4111111111111111" not in self.log_records[0].msg

    def test_mask_cvv(self):
        """Test CVV masking (context-dependent)."""
        self.logger.info("CVV: 123")

        assert len(self.log_records) == 1
        assert "CVV: ***" in self.log_records[0].msg
        assert "CVV: 123" not in self.log_records[0].msg

    def test_mask_ein(self):
        """Test Employer Identification Number masking."""
        self.logger.info("EIN: 12-3456789")

        assert len(self.log_records) == 1
        assert "**-****789" in self.log_records[0].msg
        assert "12-3456789" not in self.log_records[0].msg

    def test_mask_multiple_pii_types(self):
        """Test masking multiple PII types in same message."""
        self.logger.info("SSN: 123-45-6789, Account: 1234567890, Card: 4111 1111 1111 1111")

        assert len(self.log_records) == 1
        msg = self.log_records[0].msg
        assert "***-**-6789" in msg
        assert "******7890" in msg
        assert "**** **** **** 1111" in msg

    def test_no_false_positives(self):
        """Test that non-PII numbers are not masked."""
        self.logger.info("Order ID: 12345, Phone: 5551234")

        assert len(self.log_records) == 1
        # These should NOT be masked (no context keywords)
        assert "12345" in self.log_records[0].msg
        assert "5551234" in self.log_records[0].msg

    def test_mask_email_when_enabled(self):
        """Test email masking when enabled."""
        pii_filter = FinancialPIIFilter(mask_emails=True)
        self.logger.removeFilter(self.pii_filter)
        self.logger.addFilter(pii_filter)

        self.logger.info("Email: user@example.com")

        assert len(self.log_records) == 1
        assert "u***@example.com" in self.log_records[0].msg
        assert "user@example.com" not in self.log_records[0].msg

    def test_mask_phone_when_enabled(self):
        """Test phone number masking when enabled."""
        pii_filter = FinancialPIIFilter(mask_phones=True)
        self.logger.removeFilter(self.pii_filter)
        self.logger.addFilter(pii_filter)

        self.logger.info("Phone: (555) 123-4567")

        assert len(self.log_records) == 1
        assert "***-***-4567" in self.log_records[0].msg


class TestTokenEncryption:
    """Test provider token encryption and decryption."""

    def setup_method(self):
        """Generate test encryption key."""
        self.key = Fernet.generate_key()
        self.encryption = ProviderTokenEncryption(key=self.key)

    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption."""
        token = "plaid-sandbox-token-123"
        context = {"user_id": "user123", "provider": "plaid"}

        # Encrypt
        encrypted = self.encryption.encrypt(token, context=context)
        assert encrypted != token
        assert len(encrypted) > len(token)

        # Decrypt
        decrypted = self.encryption.decrypt(encrypted, context=context)
        assert decrypted == token

    def test_decrypt_with_wrong_context(self):
        """Test decryption fails with wrong context."""
        token = "plaid-token"
        context = {"user_id": "user123", "provider": "plaid"}
        wrong_context = {"user_id": "user456", "provider": "plaid"}

        encrypted = self.encryption.encrypt(token, context=context)

        with pytest.raises(ValueError, match="Context mismatch"):
            self.encryption.decrypt(encrypted, context=wrong_context)

    def test_decrypt_without_verification(self):
        """Test decryption without context verification."""
        token = "plaid-token"
        context = {"user_id": "user123", "provider": "plaid"}

        encrypted = self.encryption.encrypt(token, context=context)

        # Decrypt without verification
        decrypted = self.encryption.decrypt(encrypted, verify_context=False)
        assert decrypted == token

    def test_decrypt_invalid_token(self):
        """Test decryption fails with invalid token."""
        with pytest.raises(ValueError, match="Decryption failed"):
            self.encryption.decrypt("invalid-token")

    def test_key_rotation(self):
        """Test re-encrypting token with new key."""
        token = "plaid-token"
        context = {"user_id": "user123", "provider": "plaid"}

        # Encrypt with old key
        encrypted = self.encryption.encrypt(token, context=context)

        # Rotate to new key
        new_key = Fernet.generate_key()
        re_encrypted = self.encryption.rotate_key(encrypted, new_key, context=context)

        # Decrypt with new key
        new_encryption = ProviderTokenEncryption(key=new_key)
        decrypted = new_encryption.decrypt(re_encrypted, context=context)
        assert decrypted == token

    def test_generate_key(self):
        """Test key generation."""
        key = generate_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) > 0

        # Key should be valid for Fernet
        encryption = ProviderTokenEncryption(key=key)
        token = encryption.encrypt("test")
        assert encryption.decrypt(token, verify_context=False) == "test"

    def test_encryption_from_env(self):
        """Test encryption initialization from environment variable."""
        key = Fernet.generate_key()
        os.environ["PROVIDER_TOKEN_ENCRYPTION_KEY"] = key.decode()

        encryption = ProviderTokenEncryption()
        token = "test-token"

        encrypted = encryption.encrypt(token)
        decrypted = encryption.decrypt(encrypted, verify_context=False)
        assert decrypted == token

        # Cleanup
        del os.environ["PROVIDER_TOKEN_ENCRYPTION_KEY"]

    def test_encryption_missing_key(self):
        """Test encryption fails without key."""
        # Ensure env var is not set
        os.environ.pop("PROVIDER_TOKEN_ENCRYPTION_KEY", None)

        with pytest.raises(ValueError, match="Encryption key required"):
            ProviderTokenEncryption()


class TestAuditLogging:
    """Test PII access audit logging."""

    def setup_method(self):
        """Clear audit logs."""
        clear_audit_logs()

    @pytest.mark.asyncio
    async def test_log_pii_access(self):
        """Test logging PII access."""
        log_entry = await log_pii_access(
            user_id="user123",
            pii_type="ssn",
            action="read",
            resource="user:user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert log_entry.user_id == "user123"
        assert log_entry.pii_type == "ssn"
        assert log_entry.action == "read"
        assert log_entry.resource == "user:user123"
        assert log_entry.success is True

    @pytest.mark.asyncio
    async def test_get_audit_logs(self):
        """Test retrieving audit logs."""
        # Log multiple accesses
        await log_pii_access("user123", "ssn", "read", "user:user123")
        await log_pii_access("user456", "account", "write", "account:456")
        await log_pii_access("user123", "card", "read", "card:789")

        # Get all logs
        all_logs = get_audit_logs()
        assert len(all_logs) == 3

        # Filter by user
        user_logs = get_audit_logs(user_id="user123")
        assert len(user_logs) == 2

        # Filter by PII type
        ssn_logs = get_audit_logs(pii_type="ssn")
        assert len(ssn_logs) == 1
        assert ssn_logs[0].pii_type == "ssn"

    @pytest.mark.asyncio
    async def test_audit_log_ordering(self):
        """Test audit logs are ordered by timestamp descending."""
        await log_pii_access("user1", "ssn", "read", "resource1")
        await log_pii_access("user2", "account", "write", "resource2")
        await log_pii_access("user3", "card", "read", "resource3")

        logs = get_audit_logs()
        assert len(logs) == 3

        # Most recent first
        assert logs[0].user_id == "user3"
        assert logs[1].user_id == "user2"
        assert logs[2].user_id == "user1"


class TestValidation:
    """Test PII validation functions."""

    def test_luhn_checksum_valid(self):
        """Test Luhn algorithm with valid card numbers."""
        # Visa test card
        assert luhn_checksum("4111111111111111") is True

        # Mastercard test card
        assert luhn_checksum("5555555555554444") is True

        # Amex test card
        assert luhn_checksum("378282246310005") is True

    def test_luhn_checksum_invalid(self):
        """Test Luhn algorithm with invalid numbers."""
        assert luhn_checksum("1234567890123456") is False
        # Note: All zeros passes Luhn (edge case), use different invalid number
        assert luhn_checksum("1111111111111111") is False

    def test_routing_number_valid(self):
        """Test routing number validation with valid numbers."""
        # Chase Bank
        assert is_valid_routing_number("021000021") is True

        # Bank of America
        assert is_valid_routing_number("026009593") is True

    def test_routing_number_invalid(self):
        """Test routing number validation with invalid numbers."""
        assert is_valid_routing_number("123456789") is False
        # Note: All zeros passes checksum (edge case), use different invalid number
        assert is_valid_routing_number("111111111") is False
        assert is_valid_routing_number("12345678") is False  # Too short


class TestFastAPIIntegration:
    """Test FastAPI integration with add_financial_security."""

    def test_add_financial_security(self):
        """Test adding financial security to FastAPI app."""
        from fastapi import FastAPI

        app = FastAPI()
        key = Fernet.generate_key()

        encryption = add_financial_security(
            app, encryption_key=key, enable_pii_filter=True, enable_audit_log=True
        )

        assert isinstance(encryption, ProviderTokenEncryption)
        assert hasattr(app.state, "provider_token_encryption")
        assert app.state.provider_token_encryption == encryption
        assert app.state.financial_pii_filter_enabled is True
        assert app.state.financial_audit_log_enabled is True

    def test_add_financial_security_without_key(self):
        """Test security setup uses environment variable."""
        from fastapi import FastAPI

        key = Fernet.generate_key()
        os.environ["PROVIDER_TOKEN_ENCRYPTION_KEY"] = key.decode()

        app = FastAPI()
        encryption = add_financial_security(app)

        assert isinstance(encryption, ProviderTokenEncryption)

        # Cleanup
        del os.environ["PROVIDER_TOKEN_ENCRYPTION_KEY"]
