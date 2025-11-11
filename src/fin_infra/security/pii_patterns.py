"""
Financial PII detection patterns.

Regex patterns for detecting sensitive financial information in logs and text.
"""

import re

# Social Security Number (SSN)
SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b",  # With dashes: 123-45-6789
    re.IGNORECASE,
)

SSN_NO_DASH = re.compile(
    r"\b\d{9}\b",  # Without dashes: 123456789 (needs context)
    re.IGNORECASE,
)

# Bank Account Number (8-17 digits)
ACCOUNT_PATTERN = re.compile(r"\b\d{8,17}\b", re.IGNORECASE)

# ABA Routing Number (9 digits)
ROUTING_PATTERN = re.compile(
    r"\b\d{9}\b",  # Same as SSN_NO_DASH (needs context)
    re.IGNORECASE,
)

# Credit Card (major card networks)
CARD_PATTERN = re.compile(
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4,7}\b",  # 13-19 digits
    re.IGNORECASE,
)

# CVV (3-4 digits, context-dependent)
CVV_PATTERN = re.compile(r"\b\d{3,4}\b", re.IGNORECASE)

# Tax ID / Employer Identification Number (EIN)
EIN_PATTERN = re.compile(
    r"\b\d{2}-\d{7}\b",  # 12-3456789
    re.IGNORECASE,
)

# Email addresses (not PII but often sensitive)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE)

# Phone numbers (US format)
PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", re.IGNORECASE
)

# Driver's License (state-specific patterns - simplified)
DL_PATTERN = re.compile(
    r"\b[A-Z]{1,2}\d{6,8}\b",  # Simplified (CA: A1234567, TX: 12345678)
    re.IGNORECASE,
)


def luhn_checksum(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.

    Args:
        card_number: Credit card number (digits only)

    Returns:
        True if valid, False otherwise
    """

    def digits_of(n):
        return [int(d) for d in str(n)]

    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0


def is_valid_routing_number(routing: str) -> bool:
    """
    Validate ABA routing number using checksum algorithm.

    Args:
        routing: 9-digit routing number

    Returns:
        True if valid, False otherwise
    """
    if len(routing) != 9 or not routing.isdigit():
        return False

    # ABA checksum algorithm
    # 3*(d1+d4+d7) + 7*(d2+d5+d8) + 1*(d3+d6+d9) mod 10 = 0
    digits = [int(d) for d in routing]
    checksum = (
        3 * (digits[0] + digits[3] + digits[6])
        + 7 * (digits[1] + digits[4] + digits[7])
        + 1 * (digits[2] + digits[5] + digits[8])
    )
    return checksum % 10 == 0


# Context keywords that indicate nearby number is PII
SSN_CONTEXT = ["ssn", "social security", "social-security", "tax id", "taxpayer"]
ACCOUNT_CONTEXT = ["account", "acct", "account_number", "account-number"]
ROUTING_CONTEXT = ["routing", "routing_number", "routing-number", "aba"]
CARD_CONTEXT = ["card", "credit card", "debit card", "pan", "card_number"]
CVV_CONTEXT = ["cvv", "cvc", "security code", "card code"]
