"""
Security module models.

Pydantic models for security-related operations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProviderTokenMetadata(BaseModel):
    """Metadata for an encrypted provider token."""

    user_id: str = Field(..., description="User ID who owns the token")
    provider: str = Field(..., description="Provider name (plaid, alpaca, alphavantage, etc.)")
    encrypted_token: str = Field(..., description="Encrypted token (base64-encoded)")
    key_id: Optional[str] = Field(None, description="Key ID for key rotation")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Token creation timestamp"
    )
    expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last time token was used")


class PIIAccessLog(BaseModel):
    """Audit log entry for PII access."""

    user_id: str = Field(..., description="User who accessed PII")
    pii_type: str = Field(..., description="Type of PII (ssn, account, card, etc.)")
    action: str = Field(..., description="Action performed (read, write, delete)")
    resource: str = Field(..., description="Resource accessed (e.g., user:123, account:456)")
    ip_address: Optional[str] = Field(None, description="IP address of requester")
    user_agent: Optional[str] = Field(None, description="User agent string")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Access timestamp")
    success: bool = Field(True, description="Whether access was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
