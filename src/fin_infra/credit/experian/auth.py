"""OAuth 2.0 token management for Experian API.

Handles:
- Token acquisition via client credentials flow
- Token caching via svc-infra cache (Redis, 1 hour TTL)
- Automatic token refresh on cache miss

Uses svc_infra.cache for caching instead of custom in-memory cache.
This provides Redis persistence, distributed caching, and monitoring.

Example:
    >>> from svc_infra.cache import init_cache
    >>>
    >>> # Initialize cache once at startup
    >>> init_cache(url="redis://localhost:6379", prefix="finapp")
    >>>
    >>> auth = ExperianAuthManager(
    ...     client_id="your_client_id",
    ...     client_secret="your_client_secret",
    ...     base_url="https://sandbox.experian.com"
    ... )
    >>> token = await auth.get_token()
    >>> # Token is cached in Redis for 1 hour
"""

import base64

import httpx
from svc_infra.cache import cache_read
from svc_infra.cache.tags import invalidate_tags

# Cache key for OAuth tokens: "oauth_token:experian:{base_url_hash}"
# TTL: 3600 seconds (1 hour) - matches typical OAuth token expiry
# Tags: ["oauth:experian"] - for bulk invalidation if needed


class ExperianAuthManager:
    """Manages OAuth 2.0 tokens for Experian API.

    Uses client credentials flow to obtain access tokens. Tokens are cached
    via svc-infra cache (Redis) with 1 hour TTL.

    Architecture:
    - Uses svc_infra.cache.cache_read decorator for automatic caching
    - Cache key: "oauth_token:experian:{base_url_hash}"
    - Cache TTL: 3600 seconds (1 hour)
    - Cache backend: Redis (via svc-infra)

    Args:
        client_id: Experian API client ID
        client_secret: Experian API client secret
        base_url: Experian API base URL (sandbox or production)
        token_ttl: Token validity in seconds (default: 3600)
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str,
        token_ttl: int = 3600,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.token_ttl = token_ttl

    async def get_token(self) -> str:
        """Get valid access token from cache or fetch new one.

        Uses svc-infra cache decorator. On cache miss, fetches new token from
        Experian OAuth endpoint. Token is cached for 1 hour (3600s).

        Cache key includes client_id to ensure different auth managers don't
        share tokens across different credentials.

        Returns:
            Valid OAuth 2.0 access token

        Raises:
            httpx.HTTPStatusError: If token acquisition fails

        Example:
            >>> token = await auth.get_token()
            >>> headers = {"Authorization": f"Bearer {token}"}
        """
        # Call the cached implementation with client_id for cache key
        return await self._get_token_cached(client_id=self.client_id)

    @cache_read(
        key="oauth_token:experian:{client_id}",  # Use client_id for uniqueness
        ttl=3600,  # 1 hour - matches OAuth token expiry
        tags=lambda **kw: ["oauth:experian"],
    )
    async def _get_token_cached(self, *, client_id: str) -> str:
        """Cached token getter (internal method).

        Args:
            client_id: Client ID for cache key

        Returns:
            Access token string
        """
        # Cache miss - fetch new token
        return await self._fetch_token()

    async def _fetch_token(self) -> str:
        """Acquire new access token from Experian OAuth endpoint.

        Uses client credentials flow:
        1. Encode client_id:client_secret as base64
        2. POST to /oauth2/v1/token with grant_type=client_credentials
        3. Extract access_token from response

        Returns:
            Access token string

        Raises:
            httpx.HTTPStatusError: If token request fails (401, 500, etc.)
        """
        # Encode credentials as base64
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        # Request token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth2/v1/token",
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "read:credit write:credit",
                },
                timeout=10.0,
            )
            response.raise_for_status()

        # Parse and return token
        data = response.json()
        return data["access_token"]

    async def invalidate(self) -> None:
        """Invalidate cached token (force refresh on next get_token call).

        Uses svc-infra cache tag invalidation to clear all tokens with tag
        "oauth:experian". Useful when token is rejected by API.

        Example:
            >>> try:
            ...     await client.get("/endpoint")
            ... except httpx.HTTPStatusError as e:
            ...     if e.response.status_code == 401:
            ...         await auth.invalidate()
            ...         # Next get_token() will fetch new token
        """
        await invalidate_tags("oauth:experian")
