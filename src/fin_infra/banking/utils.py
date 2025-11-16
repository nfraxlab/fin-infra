"""
Banking connection utilities for applications.

Helpers for token validation, encryption, and provider management.
Apps still manage user-to-token mappings, but these utilities simplify common operations.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

from ..providers.base import BankingProvider


class BankingConnectionInfo(BaseModel):
    """Information about a banking provider connection."""
    
    provider: Literal["plaid", "teller", "mx"]
    connected: bool
    access_token: Optional[str] = Field(None, description="Token (only for internal use, never expose)")
    item_id: Optional[str] = None
    enrollment_id: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    is_healthy: bool = True
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BankingConnectionStatus(BaseModel):
    """Status of all banking connections for a user."""
    
    plaid: Optional[BankingConnectionInfo] = None
    teller: Optional[BankingConnectionInfo] = None
    mx: Optional[BankingConnectionInfo] = None
    has_any_connection: bool = False
    
    @property
    def connected_providers(self) -> list[str]:
        """List of connected provider names."""
        providers = []
        if self.plaid and self.plaid.connected:
            providers.append("plaid")
        if self.teller and self.teller.connected:
            providers.append("teller")
        if self.mx and self.mx.connected:
            providers.append("mx")
        return providers
    
    @property
    def primary_provider(self) -> Optional[str]:
        """Primary provider (first connected, or most recently synced)."""
        if not self.has_any_connection:
            return None
        
        # Preference order: plaid > teller > mx
        if self.plaid and self.plaid.connected:
            return "plaid"
        if self.teller and self.teller.connected:
            return "teller"
        if self.mx and self.mx.connected:
            return "mx"
        return None


def validate_plaid_token(access_token: str) -> bool:
    """
    Validate Plaid access token format.
    
    Args:
        access_token: Plaid access token to validate
        
    Returns:
        True if token format is valid
        
    Note:
        This only validates format, not that the token is active/unexpired.
        Use provider's API to verify token health.
    
    Example:
        >>> validate_plaid_token("access-sandbox-abc123")
        True
        >>> validate_plaid_token("invalid")
        False
    """
    if not access_token:
        return False
    
    # Plaid tokens typically start with "access-{environment}-"
    pattern = r'^access-(sandbox|development|production)-[a-zA-Z0-9-_]+$'
    return bool(re.match(pattern, access_token))


def validate_teller_token(access_token: str) -> bool:
    """
    Validate Teller access token format.
    
    Args:
        access_token: Teller access token to validate
        
    Returns:
        True if token format is valid
        
    Note:
        This only validates format, not that the token is active/unexpired.
        Use provider's API to verify token health.
    
    Example:
        >>> validate_teller_token("test_token_abc123")
        True
        >>> validate_teller_token("invalid")
        False
    """
    if not access_token:
        return False
    
    # Teller tokens are typically alphanumeric with underscores
    # Sandbox tokens often start with "test_"
    pattern = r'^[a-zA-Z0-9_-]{10,}$'
    return bool(re.match(pattern, access_token))


def validate_mx_token(access_token: str) -> bool:
    """
    Validate MX access token format.
    
    Args:
        access_token: MX access token to validate
        
    Returns:
        True if token format is valid
    
    Example:
        >>> validate_mx_token("USR-abc123")
        True
    """
    if not access_token:
        return False
    
    # MX tokens typically have a prefix like "USR-"
    pattern = r'^[A-Z]+-[a-zA-Z0-9-_]+$'
    return bool(re.match(pattern, access_token))


def validate_provider_token(provider: str, access_token: str) -> bool:
    """
    Validate token format for any provider.
    
    Args:
        provider: Provider name ("plaid", "teller", "mx")
        access_token: Token to validate
        
    Returns:
        True if token format is valid for the provider
        
    Example:
        >>> validate_provider_token("plaid", "access-sandbox-abc")
        True
        >>> validate_provider_token("teller", "test_token_123")
        True
    """
    validators = {
        "plaid": validate_plaid_token,
        "teller": validate_teller_token,
        "mx": validate_mx_token,
    }
    
    validator = validators.get(provider.lower())
    if not validator:
        # Unknown provider - do basic validation
        return bool(access_token and len(access_token) > 10)
    
    return validator(access_token)


def parse_banking_providers(banking_providers: Dict[str, Any]) -> BankingConnectionStatus:
    """
    Parse banking_providers JSON field into structured status.
    
    Args:
        banking_providers: Dictionary from User.banking_providers field
            Structure: {
                "plaid": {"access_token": "...", "item_id": "...", "connected_at": "..."},
                "teller": {"access_token": "...", "enrollment_id": "..."}
            }
            
    Returns:
        Structured status with connection info for all providers
        
    Example:
        >>> status = parse_banking_providers(user.banking_providers)
        >>> if status.has_any_connection:
        ...     print(f"Primary provider: {status.primary_provider}")
        ...     for provider in status.connected_providers:
        ...         print(f"Connected: {provider}")
    """
    status = BankingConnectionStatus()
    
    if not banking_providers:
        return status
    
    # Parse Plaid
    if "plaid" in banking_providers:
        plaid_data = banking_providers["plaid"]
        status.plaid = BankingConnectionInfo(
            provider="plaid",
            connected=bool(plaid_data.get("access_token")),
            access_token=plaid_data.get("access_token"),
            item_id=plaid_data.get("item_id"),
            connected_at=_parse_datetime(plaid_data.get("connected_at")),
            last_synced_at=_parse_datetime(plaid_data.get("last_synced_at")),
            is_healthy=plaid_data.get("is_healthy", True),
            error_message=plaid_data.get("error_message"),
        )
    
    # Parse Teller
    if "teller" in banking_providers:
        teller_data = banking_providers["teller"]
        status.teller = BankingConnectionInfo(
            provider="teller",
            connected=bool(teller_data.get("access_token")),
            access_token=teller_data.get("access_token"),
            enrollment_id=teller_data.get("enrollment_id"),
            connected_at=_parse_datetime(teller_data.get("connected_at")),
            last_synced_at=_parse_datetime(teller_data.get("last_synced_at")),
            is_healthy=teller_data.get("is_healthy", True),
            error_message=teller_data.get("error_message"),
        )
    
    # Parse MX
    if "mx" in banking_providers:
        mx_data = banking_providers["mx"]
        status.mx = BankingConnectionInfo(
            provider="mx",
            connected=bool(mx_data.get("access_token")),
            access_token=mx_data.get("access_token"),
            connected_at=_parse_datetime(mx_data.get("connected_at")),
            last_synced_at=_parse_datetime(mx_data.get("last_synced_at")),
            is_healthy=mx_data.get("is_healthy", True),
            error_message=mx_data.get("error_message"),
        )
    
    status.has_any_connection = any([
        status.plaid and status.plaid.connected,
        status.teller and status.teller.connected,
        status.mx and status.mx.connected,
    ])
    
    return status


def sanitize_connection_status(status: BankingConnectionStatus) -> Dict[str, Any]:
    """
    Sanitize connection status for API responses (removes access tokens).
    
    Args:
        status: Connection status with tokens
        
    Returns:
        Dictionary safe for API responses (no tokens)
        
    Example:
        >>> status = parse_banking_providers(user.banking_providers)
        >>> safe_data = sanitize_connection_status(status)
        >>> return {"connections": safe_data}  # Safe to return to client
    """
    result = {
        "has_any_connection": status.has_any_connection,
        "connected_providers": status.connected_providers,
        "primary_provider": status.primary_provider,
        "providers": {},
    }
    
    for provider_name in ["plaid", "teller", "mx"]:
        info = getattr(status, provider_name)
        if info:
            result["providers"][provider_name] = {
                "connected": info.connected,
                "item_id": info.item_id,
                "enrollment_id": info.enrollment_id,
                "connected_at": info.connected_at.isoformat() if info.connected_at else None,
                "last_synced_at": info.last_synced_at.isoformat() if info.last_synced_at else None,
                "is_healthy": info.is_healthy,
                "error_message": info.error_message,
                # NO access_token - this is sanitized
            }
    
    return result


def mark_connection_unhealthy(
    banking_providers: Dict[str, Any],
    provider: str,
    error_message: str,
) -> Dict[str, Any]:
    """
    Mark a provider connection as unhealthy (for error handling).
    
    Args:
        banking_providers: Current banking_providers dict
        provider: Provider name ("plaid", "teller", "mx")
        error_message: Error description
        
    Returns:
        Updated banking_providers dict
        
    Example:
        >>> try:
        ...     accounts = await banking.get_accounts(access_token)
        ... except Exception as e:
        ...     user.banking_providers = mark_connection_unhealthy(
        ...         user.banking_providers,
        ...         "plaid",
        ...         str(e)
        ...     )
        ...     await session.commit()
    """
    if provider not in banking_providers:
        return banking_providers
    
    banking_providers[provider]["is_healthy"] = False
    banking_providers[provider]["error_message"] = error_message
    banking_providers[provider]["error_at"] = datetime.now(timezone.utc).isoformat()
    
    return banking_providers


def mark_connection_healthy(
    banking_providers: Dict[str, Any],
    provider: str,
) -> Dict[str, Any]:
    """
    Mark a provider connection as healthy (after successful sync).
    
    Args:
        banking_providers: Current banking_providers dict
        provider: Provider name
        
    Returns:
        Updated banking_providers dict
        
    Example:
        >>> accounts = await banking.get_accounts(access_token)
        >>> user.banking_providers = mark_connection_healthy(
        ...     user.banking_providers,
        ...     "plaid"
        ... )
        >>> user.banking_providers[provider]["last_synced_at"] = datetime.now().isoformat()
        >>> await session.commit()
    """
    if provider not in banking_providers:
        return banking_providers
    
    banking_providers[provider]["is_healthy"] = True
    banking_providers[provider]["error_message"] = None
    banking_providers[provider]["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    
    return banking_providers


def get_primary_access_token(banking_providers: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Get the primary access token and provider name.
    
    Returns the first healthy, connected provider in priority order: plaid > teller > mx.
    
    Args:
        banking_providers: Dictionary from User.banking_providers
        
    Returns:
        Tuple of (access_token, provider_name) or (None, None)
        
    Example:
        >>> access_token, provider = get_primary_access_token(user.banking_providers)
        >>> if access_token:
        ...     banking = easy_banking(provider=provider)
        ...     accounts = await banking.get_accounts(access_token)
    """
    status = parse_banking_providers(banking_providers)
    
    # Priority order: plaid > teller > mx
    for provider_name in ["plaid", "teller", "mx"]:
        info = getattr(status, provider_name)
        if info and info.connected and info.is_healthy and info.access_token:
            return info.access_token, provider_name
    
    return None, None


async def test_connection_health(
    provider: BankingProvider,
    access_token: str,
) -> tuple[bool, Optional[str]]:
    """
    Test if a banking connection is healthy by making a lightweight API call.
    
    Args:
        provider: Banking provider instance (from easy_banking())
        access_token: Access token to test
        
    Returns:
        Tuple of (is_healthy, error_message)
        
    Example:
        >>> banking = easy_banking(provider="plaid")
        >>> is_healthy, error = await test_connection_health(banking, access_token)
        >>> if not is_healthy:
        ...     logger.error(f"Connection unhealthy: {error}")
    """
    try:
        # Try to fetch accounts (lightweight call)
        accounts = provider.accounts(access_token)
        
        # If we got here, connection is healthy
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        
        # Check for common error patterns
        if "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
            return False, "Token invalid or expired"
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, "Connection timeout"
        else:
            return False, error_msg


def should_refresh_token(banking_providers: Dict[str, Any], provider: str) -> bool:
    """
    Check if a provider token should be refreshed.
    
    Args:
        banking_providers: Current banking_providers dict
        provider: Provider name
        
    Returns:
        True if token should be refreshed
        
    Example:
        >>> if should_refresh_token(user.banking_providers, "plaid"):
        ...     # Trigger token refresh flow
        ...     pass
    """
    if provider not in banking_providers:
        return False
    
    provider_data = banking_providers[provider]
    
    # Check if marked unhealthy
    if not provider_data.get("is_healthy", True):
        return True
    
    # Check last sync time
    last_synced_str = provider_data.get("last_synced_at")
    if last_synced_str:
        last_synced = _parse_datetime(last_synced_str)
        if last_synced:
            # Refresh if not synced in 30 days
            days_since_sync = (datetime.now(timezone.utc) - last_synced).days
            if days_since_sync > 30:
                return True
    
    return False


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if not value:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        try:
            # Try ISO format
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    return None
