# Banking Connection Utilities

**Location**: `fin-infra/src/fin_infra/banking/utils.py`

## Overview

Banking connection utilities help applications manage user-to-provider token mappings while keeping the heavy lifting (data fetching, provider abstraction) in fin-infra's core banking module.

### Philosophy

- **fin-infra provides**: Provider abstraction, data fetching, utilities
- **Applications manage**: User models, token storage, authentication, user-specific connection state

This separation ensures:
- ✅ Applications control their security model (encryption, storage)
- ✅ Applications control their user model schema
- ✅ fin-infra utilities reduce boilerplate across all apps
- ✅ No forced database schema or ORM dependencies

---

## Features

### 1. Token Validation

Validate access token formats before storage:

```python
from fin_infra.banking import validate_provider_token

# Validate Plaid token
if not validate_provider_token("plaid", access_token):
    raise HTTPException(400, "Invalid token format")

# Provider-specific validators also available
from fin_infra.banking import (
    validate_plaid_token,
    validate_teller_token,
    validate_mx_token,
)
```

**Why?** Catch malformed tokens early before storing in database.

---

### 2. Connection Status Parsing

Parse the `banking_providers` JSON field into structured data:

```python
from fin_infra.banking import parse_banking_providers

status = parse_banking_providers(user.banking_providers)

# Check if any provider is connected
if status.has_any_connection:
    print(f"Primary: {status.primary_provider}")
    print(f"Connected: {status.connected_providers}")

# Access individual provider info
if status.plaid:
    print(f"Plaid connected: {status.plaid.connected}")
    print(f"Healthy: {status.plaid.is_healthy}")
    print(f"Last synced: {status.plaid.last_synced_at}")
```

**Returns**: `BankingConnectionStatus` with structured info for plaid/teller/mx

---

### 3. API Response Sanitization

Remove access tokens before returning to client:

```python
from fin_infra.banking import (
    parse_banking_providers,
    sanitize_connection_status,
)

@router.get("/status")
async def get_status(user: User = Depends(get_current_user)):
    status = parse_banking_providers(user.banking_providers)
    safe_data = sanitize_connection_status(status)
    return safe_data  # ✅ No access tokens exposed
```

**Why?** Never expose access tokens to frontend. This utility ensures safety.

---

### 4. Connection Health Management

Mark connections as healthy/unhealthy in background jobs:

```python
from fin_infra.banking import (
    mark_connection_healthy,
    mark_connection_unhealthy,
)

# In background job
try:
    accounts = await banking.get_accounts(access_token)
    
    # Success - mark healthy
    user.banking_providers = mark_connection_healthy(
        user.banking_providers,
        "plaid"
    )
    user.banking_providers["plaid"]["last_synced_at"] = datetime.now().isoformat()
    
except Exception as e:
    # Error - mark unhealthy
    user.banking_providers = mark_connection_unhealthy(
        user.banking_providers,
        "plaid",
        str(e)
    )

await session.commit()
```

**Benefits**:
- Track provider API health
- Show users which connections need attention
- Skip unhealthy connections in jobs

---

### 5. Primary Token Selection

Get the best available access token automatically:

```python
from fin_infra.banking import get_primary_access_token

# Get primary token (priority: plaid > teller > mx)
access_token, provider = get_primary_access_token(user.banking_providers)

if access_token:
    banking = easy_banking(provider=provider)
    accounts = await banking.get_accounts(access_token)
```

**Smart selection**:
1. Only returns healthy connections
2. Priority order: plaid > teller > mx
3. Returns `(None, None)` if no healthy connection

---

### 6. Connection Health Testing

Test if a token is still valid:

```python
from fin_infra.banking import test_connection_health, easy_banking

banking = easy_banking(provider="plaid")
is_healthy, error = await test_connection_health(banking, access_token)

if not is_healthy:
    logger.error(f"Token invalid: {error}")
    # Trigger re-authentication flow
```

**Why?** Lightweight health check before running expensive operations.

---

## Complete Example: Application Integration

### 1. Connect Provider Endpoint

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fin_infra.banking import validate_provider_token
from sqlalchemy import select

router = APIRouter()

@router.post("/banking-connection/plaid")
async def connect_plaid(
    request: PlaidConnectionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # Validate token format
    if not validate_provider_token("plaid", request.access_token):
        raise HTTPException(400, "Invalid token format")
    
    # Store in user's banking_providers field
    banking_providers = user.banking_providers or {}
    banking_providers["plaid"] = {
        "access_token": request.access_token,
        "item_id": request.item_id,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "is_healthy": True,
        "error_message": None,
    }
    user.banking_providers = banking_providers
    
    await session.commit()
    return {"success": True, "provider": "plaid"}
```

---

### 2. Get Status Endpoint

```python
from fin_infra.banking import parse_banking_providers, sanitize_connection_status

@router.get("/banking-connection/status")
async def get_status(
    user: User = Depends(get_current_user),
):
    # Parse and sanitize
    status = parse_banking_providers(user.banking_providers)
    safe_data = sanitize_connection_status(status)
    
    return {
        "user_id": str(user.id),
        **safe_data
    }
```

**Response**:
```json
{
  "user_id": "uuid-here",
  "has_any_connection": true,
  "connected_providers": ["plaid"],
  "primary_provider": "plaid",
  "providers": {
    "plaid": {
      "connected": true,
      "item_id": "item_123",
      "connected_at": "2025-11-16T10:00:00Z",
      "last_synced_at": "2025-11-16T12:00:00Z",
      "is_healthy": true,
      "error_message": null
    },
    "teller": {
      "connected": false
    }
  }
}
```

---

### 3. Background Job with Health Tracking

```python
from fin_infra.banking import (
    easy_banking,
    get_primary_access_token,
    mark_connection_healthy,
    mark_connection_unhealthy,
)

async def sync_transactions_job():
    async with get_async_session() as session:
        users = await session.execute(
            select(User).where(
                User.is_active == True,
                User.banking_providers != {}
            )
        )
        
        for user in users.scalars():
            # Get best available token
            access_token, provider = get_primary_access_token(user.banking_providers)
            
            if not access_token:
                continue
            
            try:
                # Fetch transactions
                banking = easy_banking(provider=provider)
                transactions = await banking.get_transactions(
                    access_token=access_token,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                # Store in database...
                
                # Mark healthy
                user.banking_providers = mark_connection_healthy(
                    user.banking_providers,
                    provider
                )
                
            except Exception as e:
                # Mark unhealthy
                user.banking_providers = mark_connection_unhealthy(
                    user.banking_providers,
                    provider,
                    str(e)
                )
                logger.error(f"Sync failed: {e}")
        
        await session.commit()
```

---

## Data Model

### Recommended `banking_providers` JSON Structure

```python
{
    "plaid": {
        "access_token": "access-sandbox-xxx",     # Required
        "item_id": "item_xxx",                    # Provider-specific
        "connected_at": "2025-11-16T10:00:00Z",   # ISO timestamp
        "last_synced_at": "2025-11-16T12:00:00Z", # ISO timestamp
        "is_healthy": True,                        # Health status
        "error_message": None,                     # Error if unhealthy
    },
    "teller": {
        "access_token": "test_token_xxx",
        "enrollment_id": "enr_xxx",
        "connected_at": "2025-11-16T11:00:00Z",
        "last_synced_at": None,                    # Not yet synced
        "is_healthy": True,
        "error_message": None,
    }
}
```

### User Model Example

```python
from sqlalchemy import Column, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON as PGJSON

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    
    # Banking provider credentials
    banking_providers: Mapped[dict] = mapped_column(
        "banking_providers",
        PGJSON,
        default=dict,
        nullable=False
    )
```

---

## Security Considerations

### 1. Token Encryption (Recommended for Production)

The utilities work with **plaintext or encrypted** tokens. For production:

```python
from fin_infra.security import ProviderTokenEncryption

encryption = ProviderTokenEncryption()

# Encrypt before storage
encrypted = encryption.encrypt(
    access_token,
    context={"user_id": str(user.id), "provider": "plaid"}
)
banking_providers["plaid"]["access_token"] = encrypted

# Decrypt before use
access_token = encryption.decrypt(
    banking_providers["plaid"]["access_token"],
    context={"user_id": str(user.id), "provider": "plaid"}
)
```

See: `fin-infra/src/fin_infra/security/encryption.py`

---

### 2. Never Expose Tokens

Always use `sanitize_connection_status()` before returning to API:

```python
# ❌ BAD - Exposes tokens
return {"providers": user.banking_providers}

# ✅ GOOD - Sanitized
status = parse_banking_providers(user.banking_providers)
return sanitize_connection_status(status)
```

---

### 3. Token Rotation

Check if tokens need refresh:

```python
from fin_infra.banking import should_refresh_token

if should_refresh_token(user.banking_providers, "plaid"):
    # Trigger Plaid token refresh flow
    # Or notify user to reconnect
    pass
```

**Checks**:
- Unhealthy connections
- Not synced in 30+ days

---

## API Reference

### Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `validate_provider_token(provider, token)` | Validate token format | `bool` |
| `parse_banking_providers(dict)` | Parse JSON into status | `BankingConnectionStatus` |
| `sanitize_connection_status(status)` | Remove tokens | `dict` |
| `get_primary_access_token(dict)` | Get best token | `(token, provider)` |
| `mark_connection_healthy(dict, provider)` | Mark healthy | `dict` |
| `mark_connection_unhealthy(dict, provider, error)` | Mark unhealthy | `dict` |
| `test_connection_health(provider, token)` | Test token | `(is_healthy, error)` |
| `should_refresh_token(dict, provider)` | Check refresh needed | `bool` |

### Models

| Model | Purpose |
|-------|---------|
| `BankingConnectionInfo` | Single provider info |
| `BankingConnectionStatus` | All providers status |

---

## Migration Guide

### Before (Manual Management)

```python
# Lots of repeated code
plaid_token = user.banking_providers.get("plaid", {}).get("access_token")
teller_token = user.banking_providers.get("teller", {}).get("access_token")
access_token = plaid_token or teller_token
provider = "plaid" if plaid_token else "teller"

# Manual sanitization
safe_data = {}
for p in ["plaid", "teller"]:
    if p in user.banking_providers:
        safe_data[p] = {
            "connected": True,
            # ... many more lines
        }
```

### After (With Utilities)

```python
from fin_infra.banking import (
    get_primary_access_token,
    parse_banking_providers,
    sanitize_connection_status,
)

# Simple token access
access_token, provider = get_primary_access_token(user.banking_providers)

# Simple sanitization
status = parse_banking_providers(user.banking_providers)
safe_data = sanitize_connection_status(status)
```

**Result**: 50% less boilerplate, consistent behavior across apps

---

## Testing

```python
from fin_infra.banking import parse_banking_providers

def test_connection_status():
    banking_providers = {
        "plaid": {
            "access_token": "access-sandbox-test",
            "item_id": "item_123",
            "connected_at": "2025-11-16T10:00:00Z",
            "is_healthy": True,
        }
    }
    
    status = parse_banking_providers(banking_providers)
    
    assert status.has_any_connection == True
    assert status.primary_provider == "plaid"
    assert status.plaid.connected == True
    assert status.plaid.is_healthy == True
```

---

## See Also

- **Core Banking**: `fin-infra/src/fin_infra/banking/__init__.py`
- **Security/Encryption**: `fin-infra/src/fin_infra/security/encryption.py`
- **Example Implementation**: `fin-api/src/fin_api/routers/v0/banking_connection.py`
- **Background Jobs**: `fin-api/src/fin_api/jobs/banking.py`
