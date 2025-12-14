from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, Iterable, TypeVar

from fin_infra.exceptions import RetryError

# Re-export for backward compatibility
__all__ = ["RetryError", "retry_async"]

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    jitter: float = 0.1,
    retry_on: Iterable[type[BaseException]] = (Exception,),
) -> T:
    """Simple async retry with exponential backoff and jitter.

    Not provider-specific; callers should keep idempotency in mind.
    """
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return await func()
        except tuple(retry_on) as exc:  # type: ignore[misc]
            last_exc = exc
            if i == attempts - 1:
                break
            delay = (2**i) * base_delay + random.uniform(0, jitter)
            await asyncio.sleep(delay)
    raise RetryError("Retry attempts exhausted") from last_exc
