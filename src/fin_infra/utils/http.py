from __future__ import annotations

from typing import Any, cast

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_DEFAULT_TIMEOUT = httpx.Timeout(20.0)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def aget_json(url: str, **kwargs) -> dict[Any, Any]:
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(url, **kwargs)
        r.raise_for_status()
        return cast("dict[Any, Any]", r.json())
