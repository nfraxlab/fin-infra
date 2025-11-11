"""
Provider token storage operations.

Database operations for encrypted provider tokens.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from .encryption import ProviderTokenEncryption
from .models import ProviderTokenMetadata

Base = declarative_base()


class ProviderToken(Base):
    """Database model for encrypted provider tokens."""

    __tablename__ = "provider_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    encrypted_token = Column(Text, nullable=False)
    key_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # Unique constraint: one token per user+provider
        {"schema": None},
    )


async def store_provider_token(
    db: AsyncSession,
    user_id: str,
    provider: str,
    token: str,
    encryption: ProviderTokenEncryption,
    expires_at: Optional[datetime] = None,
    key_id: Optional[str] = None,
) -> ProviderTokenMetadata:
    """
    Store encrypted provider token in database.

    Args:
        db: Database session
        user_id: User ID who owns the token
        provider: Provider name (plaid, alpaca, etc.)
        token: Plaintext token to encrypt and store
        encryption: Encryption instance
        expires_at: Optional token expiration timestamp
        key_id: Optional key ID for rotation

    Returns:
        Token metadata

    Example:
        >>> from fin_infra.security import ProviderTokenEncryption, store_provider_token
        >>>
        >>> encryption = ProviderTokenEncryption()
        >>> metadata = await store_provider_token(
        ...     db,
        ...     user_id="user123",
        ...     provider="plaid",
        ...     token="plaid-sandbox-token",
        ...     encryption=encryption
        ... )
    """
    # Encrypt token with context
    context = {"user_id": user_id, "provider": provider}
    encrypted = encryption.encrypt(token, context=context, key_id=key_id)

    # Check if token exists
    stmt = select(ProviderToken).where(
        ProviderToken.user_id == user_id, ProviderToken.provider == provider
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing token
        update_stmt = (
            update(ProviderToken)
            .where(ProviderToken.user_id == user_id, ProviderToken.provider == provider)
            .values(
                encrypted_token=encrypted,
                key_id=key_id,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
            )
        )
        await db.execute(update_stmt)
    else:
        # Insert new token
        token_obj = ProviderToken(
            user_id=user_id,
            provider=provider,
            encrypted_token=encrypted,
            key_id=key_id,
            expires_at=expires_at,
        )
        db.add(token_obj)

    await db.commit()

    return ProviderTokenMetadata(
        user_id=user_id,
        provider=provider,
        encrypted_token=encrypted,
        key_id=key_id,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
    )


async def get_provider_token(
    db: AsyncSession, user_id: str, provider: str, encryption: ProviderTokenEncryption
) -> str:
    """
    Retrieve and decrypt provider token from database.

    Args:
        db: Database session
        user_id: User ID who owns the token
        provider: Provider name
        encryption: Encryption instance

    Returns:
        Decrypted token

    Raises:
        ValueError: If token not found or expired

    Example:
        >>> token = await get_provider_token(db, "user123", "plaid", encryption)
    """
    # Query token
    stmt = select(ProviderToken).where(
        ProviderToken.user_id == user_id, ProviderToken.provider == provider
    )
    result = await db.execute(stmt)
    token_obj = result.scalar_one_or_none()

    if not token_obj:
        raise ValueError(f"Token not found for user {user_id} and provider {provider}")

    # Check expiration
    if token_obj.expires_at and token_obj.expires_at < datetime.utcnow():
        raise ValueError(f"Token expired at {token_obj.expires_at}")

    # Decrypt token
    context = {"user_id": user_id, "provider": provider}
    token = encryption.decrypt(token_obj.encrypted_token, context=context)

    # Update last_used_at
    update_stmt = (
        update(ProviderToken)
        .where(ProviderToken.user_id == user_id, ProviderToken.provider == provider)
        .values(last_used_at=datetime.utcnow())
    )
    await db.execute(update_stmt)
    await db.commit()

    return token


async def delete_provider_token(db: AsyncSession, user_id: str, provider: str) -> bool:
    """
    Delete provider token from database.

    Args:
        db: Database session
        user_id: User ID who owns the token
        provider: Provider name

    Returns:
        True if token was deleted, False if not found

    Example:
        >>> deleted = await delete_provider_token(db, "user123", "plaid")
    """
    stmt = select(ProviderToken).where(
        ProviderToken.user_id == user_id, ProviderToken.provider == provider
    )
    result = await db.execute(stmt)
    token_obj = result.scalar_one_or_none()

    if not token_obj:
        return False

    await db.delete(token_obj)
    await db.commit()
    return True
