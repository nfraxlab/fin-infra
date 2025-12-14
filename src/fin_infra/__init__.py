"""fin_infra: Financial infrastructure toolkit.

Public surface is intentionally small at this stage. Import from submodules for
specific domains (clients, models, markets, credit).
"""

from .exceptions import (
    FinInfraError,
    ProviderError,
    ProviderNotFoundError,
    ValidationError,
)
from .version import __version__

__all__ = [
    "__version__",
    # Base errors
    "FinInfraError",
    "ProviderError",
    "ProviderNotFoundError",
    "ValidationError",
]
