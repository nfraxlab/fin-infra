"""Unified exception hierarchy for fin-infra.

This module provides a consistent exception hierarchy across all fin-infra components:
- Provider errors (API failures, authentication, rate limits)
- Normalization errors (currency, symbol resolution)
- Validation errors (data validation, compliance)
- Calculation errors (financial calculations)

All exceptions inherit from FinInfraError, allowing users to catch all library
errors with a single except clause.

Example:
    try:
        accounts = await banking.get_accounts(token)
    except FinInfraError as e:
        print(f"Error: {e}")
        if e.hint:
            print(f"Hint: {e.hint}")
"""

from __future__ import annotations

import logging
from typing import Any

# =============================================================================
# Logging Helper
# =============================================================================


def log_exception(
    logger: logging.Logger,
    msg: str,
    exc: Exception,
    *,
    level: str = "warning",
    include_traceback: bool = True,
) -> None:
    """Log an exception with consistent formatting.

    Use this helper instead of bare `except Exception:` blocks to ensure
    all exceptions are properly logged with context.

    Args:
        logger: The logger instance to use
        msg: Context message describing what operation failed
        exc: The exception that was caught
        level: Log level - "debug", "info", "warning", "error", "critical"
        include_traceback: Whether to include full traceback (exc_info=True)

    Example:
        try:
            result = await provider.get_data()
        except Exception as e:
            log_exception(logger, "Failed to fetch data from provider", e)
            # Handle gracefully or re-raise
    """
    log_func = getattr(logger, level.lower(), logger.warning)
    log_func(f"{msg}: {type(exc).__name__}: {exc}", exc_info=include_traceback)


# =============================================================================
# Base Error
# =============================================================================


class FinInfraError(Exception):
    """Base exception for all fin-infra errors.

    All fin-infra exceptions inherit from this, allowing users to catch
    all library errors with a single except clause.

    Attributes:
        message: Human-readable error description
        details: Additional context as key-value pairs
        hint: Suggested fix or action
        docs_url: Link to relevant documentation
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
        docs_url: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.hint = hint
        self.docs_url = docs_url

        # Build full message
        full_msg = message
        if hint:
            full_msg += f"\n  Hint: {hint}"
        if docs_url:
            full_msg += f"\n  Docs: {docs_url}"

        super().__init__(full_msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


# =============================================================================
# Provider Errors
# =============================================================================


class ProviderError(FinInfraError):
    """Base error for provider operations (banking, brokerage, credit, etc.).

    Raised when a financial data provider returns an error.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
        docs_url: str | None = None,
    ):
        self.provider = provider
        self.status_code = status_code

        # Add provider info to details
        full_details = details or {}
        if provider:
            full_details["provider"] = provider
        if status_code:
            full_details["status_code"] = status_code

        super().__init__(message, details=full_details, hint=hint, docs_url=docs_url)


class ProviderNotFoundError(ProviderError):
    """Provider not found in registry."""

    def __init__(
        self,
        provider_key: str,
        *,
        available_providers: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ):
        hint = None
        if available_providers:
            hint = f"Available providers: {', '.join(available_providers)}"

        super().__init__(
            f"Provider '{provider_key}' not found",
            details=details,
            hint=hint,
        )
        self.provider_key = provider_key
        self.available_providers = available_providers


class ProviderAPIError(ProviderError):
    """API error from a provider."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        error_type: str | None = None,
        response: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        self.error_type = error_type
        self.response = response

        full_details = details or {}
        if error_type:
            full_details["error_type"] = error_type
        if response:
            full_details["response"] = response

        super().__init__(
            message,
            provider=provider,
            status_code=status_code,
            details=full_details,
            hint=hint,
        )


class ProviderAuthError(ProviderAPIError):
    """Authentication failed with provider (401)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        provider: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        hint = "Check your API credentials"
        if provider:
            hint = f"Check your {provider.upper()} API credentials"

        super().__init__(
            message,
            provider=provider,
            status_code=401,
            error_type="Unauthorized",
            details=details,
            hint=hint,
        )


class ProviderRateLimitError(ProviderAPIError):
    """Rate limit exceeded from provider (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        provider: str | None = None,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.retry_after = retry_after

        hint = "Wait and retry the request"
        if retry_after:
            hint = f"Retry after {retry_after} seconds"

        full_details = details or {}
        if retry_after:
            full_details["retry_after"] = retry_after

        super().__init__(
            message,
            provider=provider,
            status_code=429,
            error_type="Too Many Requests",
            details=full_details,
            hint=hint,
        )


class ProviderNotFoundResourceError(ProviderAPIError):
    """Resource not found at provider (404)."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id

        full_details = details or {}
        if resource_type:
            full_details["resource_type"] = resource_type
        if resource_id:
            full_details["resource_id"] = resource_id

        super().__init__(
            message,
            provider=provider,
            status_code=404,
            error_type="Not Found",
            details=full_details,
        )


# =============================================================================
# Credit Provider Errors (Experian, Equifax, TransUnion)
# =============================================================================


class CreditError(ProviderError):
    """Base error for credit bureau operations."""

    pass


class ExperianAPIError(CreditError):
    """Error from Experian API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        self.response = response

        full_details = details or {}
        if response:
            full_details["response"] = response

        super().__init__(
            message,
            provider="experian",
            status_code=status_code,
            details=full_details,
            hint=hint,
        )


class ExperianRateLimitError(ExperianAPIError):
    """Experian rate limit exceeded (429)."""

    def __init__(
        self,
        message: str = "Experian rate limit exceeded",
        *,
        status_code: int | None = 429,
        response: dict[str, Any] | None = None,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.retry_after = retry_after

        hint = "Wait and retry the request"
        if retry_after:
            hint = f"Retry after {retry_after} seconds"

        super().__init__(
            message,
            status_code=status_code,
            response=response,
            details=details,
            hint=hint,
        )


class ExperianAuthError(ExperianAPIError):
    """Experian authentication failed (401)."""

    def __init__(
        self,
        message: str = "Experian authentication failed",
        *,
        status_code: int | None = 401,
        response: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            response=response,
            details=details,
            hint="Check your EXPERIAN_CLIENT_ID and EXPERIAN_CLIENT_SECRET",
        )


class ExperianNotFoundError(ExperianAPIError):
    """User not found in Experian bureau (404)."""

    def __init__(
        self,
        message: str = "User not found in credit bureau",
        *,
        status_code: int | None = 404,
        response: dict[str, Any] | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.user_id = user_id

        full_details = details or {}
        if user_id:
            full_details["user_id"] = user_id

        super().__init__(
            message,
            status_code=status_code,
            response=response,
            details=full_details,
        )


# =============================================================================
# Normalization Errors
# =============================================================================


class NormalizationError(FinInfraError):
    """Base error for normalization operations."""

    pass


class CurrencyNotSupportedError(NormalizationError):
    """Currency code not supported."""

    def __init__(
        self,
        currency: str,
        *,
        supported_currencies: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ):
        hint = None
        if supported_currencies:
            # Show first 10 currencies as example
            examples = supported_currencies[:10]
            hint = f"Supported currencies include: {', '.join(examples)}..."

        super().__init__(
            f"Currency '{currency}' is not supported",
            details=details,
            hint=hint,
        )
        self.currency = currency
        self.supported_currencies = supported_currencies


class SymbolNotFoundError(NormalizationError):
    """Symbol could not be resolved."""

    def __init__(
        self,
        identifier: str,
        *,
        source_format: str | None = None,
        target_format: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        msg = f"Symbol '{identifier}' could not be resolved"
        if source_format and target_format:
            msg = f"Cannot convert '{identifier}' from {source_format} to {target_format}"

        full_details = details or {}
        if source_format:
            full_details["source_format"] = source_format
        if target_format:
            full_details["target_format"] = target_format

        super().__init__(msg, details=full_details)
        self.identifier = identifier
        self.source_format = source_format
        self.target_format = target_format


class ExchangeRateAPIError(NormalizationError):
    """Error from exchange rate API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.status_code = status_code

        full_details = details or {}
        if status_code:
            full_details["status_code"] = status_code

        super().__init__(message, details=full_details)


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(FinInfraError):
    """Base error for validation failures."""

    pass


class ComplianceError(ValidationError):
    """Compliance validation failed (FCRA, PCI-DSS, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        regulation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.regulation = regulation

        full_details = details or {}
        if regulation:
            full_details["regulation"] = regulation

        super().__init__(message, details=full_details)


# =============================================================================
# Calculation Errors
# =============================================================================


class CalculationError(FinInfraError):
    """Base error for financial calculation failures."""

    pass


class InsufficientDataError(CalculationError):
    """Not enough data to perform calculation."""

    def __init__(
        self,
        message: str,
        *,
        required_fields: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.required_fields = required_fields

        full_details = details or {}
        if required_fields:
            full_details["required_fields"] = required_fields

        hint = None
        if required_fields:
            hint = f"Required fields: {', '.join(required_fields)}"

        super().__init__(message, details=full_details, hint=hint)


# =============================================================================
# Retry/Network Errors
# =============================================================================


class RetryError(FinInfraError):
    """Retry limit exceeded after multiple attempts."""

    def __init__(
        self,
        message: str = "Operation failed after max retries",
        *,
        attempts: int | None = None,
        last_exception: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.attempts = attempts
        self.last_exception = last_exception

        full_details = details or {}
        if attempts:
            full_details["attempts"] = attempts
        if last_exception:
            full_details["last_exception"] = str(last_exception)

        super().__init__(message, details=full_details)


# =============================================================================
# Convenience aliases for backward compatibility
# =============================================================================

# Keep short names for commonly used errors
APIError = ProviderAPIError
AuthError = ProviderAuthError
RateLimitError = ProviderRateLimitError
NotFoundError = ProviderNotFoundResourceError


__all__ = [
    # Logging helper
    "log_exception",
    # Base
    "FinInfraError",
    # Provider errors
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderAPIError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderNotFoundResourceError",
    # Credit provider errors
    "CreditError",
    "ExperianAPIError",
    "ExperianRateLimitError",
    "ExperianAuthError",
    "ExperianNotFoundError",
    # Normalization errors
    "NormalizationError",
    "CurrencyNotSupportedError",
    "SymbolNotFoundError",
    "ExchangeRateAPIError",
    # Validation errors
    "ValidationError",
    "ComplianceError",
    # Calculation errors
    "CalculationError",
    "InsufficientDataError",
    # Retry errors
    "RetryError",
    # Aliases
    "APIError",
    "AuthError",
    "RateLimitError",
    "NotFoundError",
]
