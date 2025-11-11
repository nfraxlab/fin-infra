"""Utilities namespace for fin-infra.

Networking timeouts/retries and related resource limits are provided by svc-infra
and should be consumed from there in services. This package intentionally keeps
no local HTTP/retry wrappers to avoid duplication.

Scaffold utilities for template-based code generation are provided by svc-infra
and should be imported from there:
    from svc_infra.utils import render_template, write, ensure_init_py
"""

__all__ = []
