"""
Financial security setup.

Easy integration of financial PII masking and token encryption.
"""

import logging
from typing import Optional

from fastapi import FastAPI

from .encryption import ProviderTokenEncryption
from .pii_filter import FinancialPIIFilter


def add_financial_security(
    app: FastAPI,
    encryption_key: Optional[bytes] = None,
    enable_pii_filter: bool = True,
    enable_audit_log: bool = True,
    mask_emails: bool = False,
    mask_phones: bool = False,
) -> ProviderTokenEncryption:
    """
    Add financial security to FastAPI application.

    Configures:
    - PII masking in logs (SSN, account numbers, cards, etc.)
    - Provider token encryption at rest
    - PII access audit logging

    Args:
        app: FastAPI application
        encryption_key: Token encryption key (uses PROVIDER_TOKEN_ENCRYPTION_KEY env if None)
        enable_pii_filter: Enable PII masking in logs (default: True)
        enable_audit_log: Enable PII access audit logging (default: True)
        mask_emails: Mask email addresses in logs (default: False)
        mask_phones: Mask phone numbers in logs (default: False)

    Returns:
        Configured ProviderTokenEncryption instance

    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.security import add_financial_security
        >>>
        >>> app = FastAPI()
        >>> encryption = add_financial_security(app)
        >>>
        >>> # Now all logs are PII-safe and tokens can be encrypted
    """
    # Initialize encryption
    encryption = ProviderTokenEncryption(key=encryption_key)

    # Add PII filter to all loggers
    if enable_pii_filter:
        pii_filter = FinancialPIIFilter(mask_emails=mask_emails, mask_phones=mask_phones)

        # Add to root logger (affects all loggers)
        root_logger = logging.getLogger()
        root_logger.addFilter(pii_filter)

        # Add to uvicorn access logger
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addFilter(pii_filter)

        logging.info("Financial PII filter enabled")

    # Store encryption instance on app state
    app.state.provider_token_encryption = encryption
    app.state.financial_pii_filter_enabled = enable_pii_filter
    app.state.financial_audit_log_enabled = enable_audit_log

    return encryption


def generate_encryption_key() -> bytes:
    """
    Generate new encryption key for provider tokens.

    Returns:
        32-byte encryption key (base64-encoded)

    Example:
        >>> from fin_infra.security import generate_encryption_key
        >>> key = generate_encryption_key()
        >>> print(f"PROVIDER_TOKEN_ENCRYPTION_KEY={key.decode()}")
    """
    return ProviderTokenEncryption.generate_key()
