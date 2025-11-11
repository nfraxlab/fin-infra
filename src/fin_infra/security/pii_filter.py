"""
Financial PII logging filter.

Automatically detects and masks financial PII in log messages.
"""

import logging
import re
from typing import Any

from .pii_patterns import (
    ACCOUNT_PATTERN,
    ACCOUNT_CONTEXT,
    CARD_PATTERN,
    CVV_PATTERN,
    CVV_CONTEXT,
    EIN_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    ROUTING_PATTERN,
    ROUTING_CONTEXT,
    SSN_PATTERN,
    SSN_NO_DASH,
    SSN_CONTEXT,
    luhn_checksum,
    is_valid_routing_number,
)


class FinancialPIIFilter(logging.Filter):
    """
    Logging filter that masks financial PII.

    Automatically detects and masks:
    - Social Security Numbers (SSN)
    - Bank account numbers
    - Routing numbers
    - Credit card numbers
    - CVV codes
    - Tax IDs (EIN)
    - Email addresses
    - Phone numbers

    Example:
        >>> import logging
        >>> from fin_infra.security import FinancialPIIFilter
        >>>
        >>> logger = logging.getLogger()
        >>> logger.addFilter(FinancialPIIFilter())
        >>>
        >>> logger.info("Processing SSN: 123-45-6789")
        >>> # Output: Processing SSN: ***-**-6789
    """

    def __init__(self, mask_emails: bool = False, mask_phones: bool = False):
        """
        Initialize PII filter.

        Args:
            mask_emails: If True, mask email addresses (default: False)
            mask_phones: If True, mask phone numbers (default: False)
        """
        super().__init__()
        self.mask_emails = mask_emails
        self.mask_phones = mask_phones

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Mask PII in log record before emission.

        Args:
            record: Log record to filter

        Returns:
            True (always emit record, but with masked PII)
        """
        # Handle string messages
        if isinstance(record.msg, str):
            record.msg = self._mask_all_pii(record.msg)

        # Handle formatted args
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_if_string(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._mask_if_string(arg) for arg in record.args)

        return True

    def _mask_if_string(self, value: Any) -> Any:
        """Mask value if it's a string, otherwise return unchanged."""
        if isinstance(value, str):
            return self._mask_all_pii(value)
        return value

    def _mask_all_pii(self, text: str) -> str:
        """Apply all PII masking rules to text."""
        # Order matters: most specific first
        text = self._mask_ssn(text)
        text = self._mask_ein(text)
        text = self._mask_card(text)
        text = self._mask_routing(text)
        text = self._mask_account(text)
        text = self._mask_cvv(text)

        if self.mask_emails:
            text = self._mask_email(text)

        if self.mask_phones:
            text = self._mask_phone(text)

        return text

    def _mask_ssn(self, text: str) -> str:
        """
        Mask Social Security Numbers.

        Examples:
            123-45-6789 → ***-**-6789
            123456789 → *****6789 (with context)
        """
        # With dashes (high confidence)
        text = SSN_PATTERN.sub(lambda m: f"***-**-{m.group()[-4:]}", text)

        # Without dashes (needs context)
        def mask_ssn_no_dash(match):
            number = match.group()
            text_lower = text.lower()

            # Check for SSN context keywords nearby
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            context = text_lower[start_pos:end_pos]

            if any(keyword in context for keyword in SSN_CONTEXT):
                return f"*****{number[-4:]}"

            return number  # Not SSN, leave unchanged

        text = SSN_NO_DASH.sub(mask_ssn_no_dash, text)
        return text

    def _mask_ein(self, text: str) -> str:
        """
        Mask Employer Identification Numbers.

        Example:
            12-3456789 → **-****789
        """
        return EIN_PATTERN.sub(lambda m: f"**-****{m.group()[-3:]}", text)

    def _mask_card(self, text: str) -> str:
        """
        Mask credit card numbers using Luhn validation.

        Examples:
            4111 1111 1111 1111 → **** **** **** 1111
            4111111111111111 → ************1111
        """

        def mask_card_match(match):
            card_str = match.group()
            # Remove spaces and dashes for validation
            digits_only = card_str.replace(" ", "").replace("-", "")

            # Validate with Luhn algorithm
            if len(digits_only) >= 13 and luhn_checksum(digits_only):
                # Preserve original formatting
                if " " in card_str:
                    return f"**** **** **** {digits_only[-4:]}"
                elif "-" in card_str:
                    return f"****-****-****-{digits_only[-4:]}"
                else:
                    return f"{'*' * (len(digits_only) - 4)}{digits_only[-4:]}"

            return card_str  # Not a valid card

        return CARD_PATTERN.sub(mask_card_match, text)

    def _mask_routing(self, text: str) -> str:
        """
        Mask ABA routing numbers with checksum validation.

        Example:
            021000021 → ******021
        """

        def mask_routing_match(match):
            number = match.group()
            text_lower = text.lower()

            # Check for routing context
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            context = text_lower[start_pos:end_pos]

            if any(keyword in context for keyword in ROUTING_CONTEXT):
                if is_valid_routing_number(number):
                    return f"******{number[-3:]}"

            return number  # Not routing, leave unchanged

        return ROUTING_PATTERN.sub(mask_routing_match, text)

    def _mask_account(self, text: str) -> str:
        """
        Mask bank account numbers.

        Example:
            1234567890 → ******7890
        """

        def mask_account_match(match):
            number = match.group()
            text_lower = text.lower()

            # Check for account context
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            context = text_lower[start_pos:end_pos]

            if any(keyword in context for keyword in ACCOUNT_CONTEXT):
                return f"{'*' * (len(number) - 4)}{number[-4:]}"

            return number  # Not account, leave unchanged

        return ACCOUNT_PATTERN.sub(mask_account_match, text)

    def _mask_cvv(self, text: str) -> str:
        """
        Mask CVV codes (context-dependent).

        Example:
            CVV: 123 → CVV: ***
        """

        def mask_cvv_match(match):
            number = match.group()
            text_lower = text.lower()

            # Check for CVV context
            start_pos = max(0, match.start() - 30)
            end_pos = min(len(text), match.end() + 30)
            context = text_lower[start_pos:end_pos]

            if any(keyword in context for keyword in CVV_CONTEXT):
                return "*" * len(number)

            return number  # Not CVV, leave unchanged

        return CVV_PATTERN.sub(mask_cvv_match, text)

    def _mask_email(self, text: str) -> str:
        """
        Mask email addresses.

        Example:
            user@example.com → u***@example.com
        """

        def mask_email_match(match):
            email = match.group()
            local, domain = email.split("@")
            if len(local) <= 2:
                return f"***@{domain}"
            return f"{local[0]}***@{domain}"

        return EMAIL_PATTERN.sub(mask_email_match, text)

    def _mask_phone(self, text: str) -> str:
        """
        Mask phone numbers.

        Example:
            (555) 123-4567 → (***) ***-4567
        """

        def mask_phone_match(match):
            phone = match.group()
            # Keep last 4 digits
            digits = re.sub(r"\D", "", phone)
            return f"***-***-{digits[-4:]}"

        return PHONE_PATTERN.sub(mask_phone_match, text)
