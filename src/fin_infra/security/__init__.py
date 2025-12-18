"""
Financial security module.

Provides:
- PII detection and masking for logs
- Provider token encryption at rest
- PII access audit logging
"""

from .add import add_financial_security, generate_encryption_key
from .audit import clear_audit_logs, get_audit_logs, log_pii_access
from .encryption import ProviderTokenEncryption
from .models import PIIAccessLog, ProviderTokenMetadata
from .pii_filter import FinancialPIIFilter
from .pii_patterns import (
    ACCOUNT_PATTERN,
    CARD_PATTERN,
    CVV_PATTERN,
    EIN_PATTERN,
    ROUTING_PATTERN,
    SSN_PATTERN,
    is_valid_routing_number,
    luhn_checksum,
)
from .token_store import (
    ProviderToken,
    delete_provider_token,
    get_provider_token,
    store_provider_token,
)

__all__ = [
    # Easy setup
    "add_financial_security",
    "generate_encryption_key",
    # PII filtering
    "FinancialPIIFilter",
    "SSN_PATTERN",
    "ACCOUNT_PATTERN",
    "ROUTING_PATTERN",
    "CARD_PATTERN",
    "CVV_PATTERN",
    "EIN_PATTERN",
    "luhn_checksum",
    "is_valid_routing_number",
    # Token encryption
    "ProviderTokenEncryption",
    "store_provider_token",
    "get_provider_token",
    "delete_provider_token",
    "ProviderToken",
    # Audit logging
    "log_pii_access",
    "get_audit_logs",
    "clear_audit_logs",
    # Models
    "ProviderTokenMetadata",
    "PIIAccessLog",
]
