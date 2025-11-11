"""
PII access audit logging.

Track access to sensitive financial data for compliance.
"""

import logging
from datetime import datetime
from typing import Optional

from .models import PIIAccessLog

logger = logging.getLogger(__name__)


# In-memory audit log (for simple use cases)
# Production should use database storage
_audit_log: list[PIIAccessLog] = []


async def log_pii_access(
    user_id: str,
    pii_type: str,
    action: str,
    resource: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> PIIAccessLog:
    """
    Log PII access for audit trail.

    Args:
        user_id: User who accessed PII
        pii_type: Type of PII (ssn, account, card, routing, etc.)
        action: Action performed (read, write, delete)
        resource: Resource accessed (e.g., user:123, account:456)
        ip_address: IP address of requester
        user_agent: User agent string
        success: Whether access was successful
        error_message: Error message if failed

    Returns:
        Audit log entry

    Example:
        >>> await log_pii_access(
        ...     user_id="user123",
        ...     pii_type="ssn",
        ...     action="read",
        ...     resource="user:user123",
        ...     ip_address="192.168.1.1"
        ... )
    """
    log_entry = PIIAccessLog(
        user_id=user_id,
        pii_type=pii_type,
        action=action,
        resource=resource,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message,
        timestamp=datetime.utcnow(),
    )

    # Store in memory (production should use database)
    _audit_log.append(log_entry)

    # Log to standard logger
    logger.info(
        f"PII access: user={user_id} type={pii_type} action={action} "
        f"resource={resource} success={success}",
        extra={
            "user_id": user_id,
            "pii_type": pii_type,
            "action": action,
            "resource": resource,
            "ip_address": ip_address,
            "success": success,
        },
    )

    return log_entry


def get_audit_logs(
    user_id: Optional[str] = None,
    pii_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> list[PIIAccessLog]:
    """
    Retrieve audit logs with optional filters.

    Args:
        user_id: Filter by user ID
        pii_type: Filter by PII type
        action: Filter by action
        limit: Maximum number of logs to return

    Returns:
        List of audit log entries

    Example:
        >>> logs = get_audit_logs(user_id="user123", pii_type="ssn")
    """
    filtered_logs = _audit_log

    if user_id:
        filtered_logs = [log for log in filtered_logs if log.user_id == user_id]

    if pii_type:
        filtered_logs = [log for log in filtered_logs if log.pii_type == pii_type]

    if action:
        filtered_logs = [log for log in filtered_logs if log.action == action]

    # Sort by timestamp descending
    filtered_logs = sorted(filtered_logs, key=lambda log: log.timestamp, reverse=True)

    return filtered_logs[:limit]


def clear_audit_logs() -> None:
    """Clear all audit logs (for testing only)."""
    global _audit_log
    _audit_log = []
