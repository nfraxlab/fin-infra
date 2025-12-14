"""Utilities namespace for fin-infra.

Networking timeouts/retries and related resource limits are provided by svc-infra
and should be consumed from there in services. This package intentionally keeps
no local HTTP/retry wrappers to avoid duplication.

Scaffold utilities for template-based code generation are provided by svc-infra
and should be imported from there:
    from svc_infra.utils import render_template, write, ensure_init_py

For async retry with exponential backoff:
    from fin_infra.utils.retry import retry_async, RetryError
"""

from fin_infra.utils.retry import RetryError, retry_async

__all__ = ["RetryError", "retry_async"]
