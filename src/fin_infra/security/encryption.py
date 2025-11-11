"""
Provider token encryption.

Encrypt/decrypt financial provider API tokens at rest.
"""

import base64
import json
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken


class ProviderTokenEncryption:
    """
    Encrypt and decrypt provider API tokens.

    Uses Fernet (symmetric encryption) with AES-128-CBC.
    Keys should be 32 bytes (base64-encoded).

    Example:
        >>> from fin_infra.security import ProviderTokenEncryption
        >>>
        >>> # Generate key (one-time)
        >>> key = Fernet.generate_key()
        >>> print(f"PROVIDER_TOKEN_ENCRYPTION_KEY={key.decode()}")
        >>>
        >>> # Encrypt token
        >>> encryption = ProviderTokenEncryption(key=key)
        >>> encrypted = encryption.encrypt(
        ...     "plaid-sandbox-token-123",
        ...     context={"user_id": "user123", "provider": "plaid"}
        ... )
        >>>
        >>> # Decrypt token
        >>> token = encryption.decrypt(encrypted, context={"user_id": "user123", "provider": "plaid"})
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize token encryption.

        Args:
            key: 32-byte encryption key (base64-encoded).
                 If None, loads from PROVIDER_TOKEN_ENCRYPTION_KEY env var.

        Raises:
            ValueError: If key is missing or invalid
        """
        if key is None:
            key_str = os.getenv("PROVIDER_TOKEN_ENCRYPTION_KEY")
            if not key_str:
                raise ValueError(
                    "Encryption key required. Set PROVIDER_TOKEN_ENCRYPTION_KEY env var "
                    "or pass key parameter. Generate with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            key = key_str.encode()

        try:
            self._fernet = Fernet(key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}") from e

    def encrypt(
        self, token: str, context: Optional[Dict[str, Any]] = None, key_id: Optional[str] = None
    ) -> str:
        """
        Encrypt provider token with optional context.

        Context prevents token reuse across users/providers.

        Args:
            token: Provider API token to encrypt
            context: Contextual data (user_id, provider, etc.)
            key_id: Key ID for key rotation (future use)

        Returns:
            Base64-encoded encrypted token

        Example:
            >>> encrypted = encryption.encrypt(
            ...     "plaid-token-123",
            ...     context={"user_id": "user123", "provider": "plaid"}
            ... )
        """
        # Package token with context
        data = {
            "token": token,
            "context": context or {},
        }

        if key_id:
            data["key_id"] = key_id

        # Serialize and encrypt
        json_data = json.dumps(data).encode()
        encrypted_bytes = self._fernet.encrypt(json_data)

        # Return base64-encoded
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(
        self,
        encrypted_token: str,
        context: Optional[Dict[str, Any]] = None,
        verify_context: bool = True,
    ) -> str:
        """
        Decrypt provider token and verify context.

        Args:
            encrypted_token: Base64-encoded encrypted token
            context: Expected context (must match encryption context)
            verify_context: If True, verify context matches (default: True)

        Returns:
            Decrypted provider token

        Raises:
            ValueError: If decryption fails or context mismatch

        Example:
            >>> token = encryption.decrypt(
            ...     encrypted,
            ...     context={"user_id": "user123", "provider": "plaid"}
            ... )
        """
        try:
            # Decode base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())

            # Decrypt
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            data = json.loads(decrypted_bytes.decode())

            # Verify context if requested
            if verify_context and context is not None:
                stored_context = data.get("context", {})
                if stored_context != context:
                    raise ValueError(
                        f"Context mismatch. Expected {context}, got {stored_context}. "
                        "Token may have been tampered with or used for wrong user/provider."
                    )

            return data["token"]

        except InvalidToken as e:
            raise ValueError(
                "Invalid encrypted token. Token may be corrupted or tampered with."
            ) from e
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e

    def rotate_key(
        self, encrypted_token: str, new_key: bytes, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Re-encrypt token with new key (for key rotation).

        Args:
            encrypted_token: Token encrypted with old key
            new_key: New encryption key
            context: Token context

        Returns:
            Token encrypted with new key

        Example:
            >>> new_key = Fernet.generate_key()
            >>> re_encrypted = encryption.rotate_key(encrypted, new_key, context={...})
        """
        # Decrypt with old key
        token = self.decrypt(encrypted_token, context=context, verify_context=False)

        # Encrypt with new key
        new_encryption = ProviderTokenEncryption(key=new_key)
        return new_encryption.encrypt(token, context=context)

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate new encryption key.

        Returns:
            32-byte encryption key (base64-encoded)

        Example:
            >>> key = ProviderTokenEncryption.generate_key()
            >>> print(f"PROVIDER_TOKEN_ENCRYPTION_KEY={key.decode()}")
        """
        return Fernet.generate_key()
