# Landing Page Cards Fix - Implementation Summary

## Problem
fin-infra capabilities (banking, market data) were not appearing as separate cards on the FastAPI documentation landing page at `/`, unlike svc-infra capabilities (/auth, /payments) which do show as cards.

## Root Cause
Routes were mounted with `app.include_router()` but the landing page card generation system in svc-infra requires explicit registration via `add_prefixed_docs()`.

## Solution
Added `add_prefixed_docs()` calls to both capability registration functions:

### 1. Banking (`src/fin_infra/banking/__init__.py`)
Added after `app.include_router()`:
```python
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
add_prefixed_docs(
    app,
    prefix=prefix,
    title="Banking",
    auto_exclude_from_root=True,
    visible_envs=None,  # Show in all environments
)
```

### 2. Market Data (`src/fin_infra/markets/__init__.py`)
Added after `app.include_router()`:
```python
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
add_prefixed_docs(
    app,
    prefix=prefix,
    title="Market Data",
    auto_exclude_from_root=True,
    visible_envs=None,  # Show in all environments
)
```

## What `add_prefixed_docs()` Does

1. **Landing Page Card**: Creates clickable card on landing page (`/`) with capability title
2. **Scoped OpenAPI**: Generates `{prefix}/openapi.json` with only that capability's routes
3. **Dedicated Swagger UI**: Provides `{prefix}/docs` showing only capability documentation
4. **Dedicated ReDoc**: Provides `{prefix}/redoc` for alternative docs view
5. **Root Exclusion**: Removes capability routes from root `/docs` (keeps root clean)
6. **Environment Filtering**: Controls which environments show the card

## Documentation Updates

### 1. copilot-instructions.md
- Updated "FastAPI Helper Requirements" section
- Added `add_prefixed_docs()` call to example code
- Added "Why `add_prefixed_docs()` is required" explanation with 6 bullet points

### 2. plans.md
- Added `add_prefixed_docs()` to "Implementation Checklist for Each Capability"
- Updated "Correct Implementation Pattern" example with full call
- Added new section: "Landing Page Cards via `add_prefixed_docs()`" with:
  - What it does (6 points)
  - What happens without it (4 points)
  - Example usage pattern

## Testing
Created `tests/test_cards_app.py` to verify cards appear:
- Mounts banking at `/banking`
- Mounts market data at `/market`
- Expected cards: "Banking" and "Market Data" on landing page

To test:
```bash
cd fin-infra
python tests/test_cards_app.py
# Visit http://localhost:8000/ and verify cards appear
```

## Files Changed
1. `/Users/alikhatami/ide/infra/fin-infra/src/fin_infra/banking/__init__.py` - Added `add_prefixed_docs()` call
2. `/Users/alikhatami/ide/infra/fin-infra/src/fin_infra/markets/__init__.py` - Added `add_prefixed_docs()` call
3. `/Users/alikhatami/ide/infra/fin-infra/.github/copilot-instructions.md` - Updated requirements and examples
4. `/Users/alikhatami/ide/infra/fin-infra/.github/plans.md` - Updated checklist and added explanation section
5. `/Users/alikhatami/ide/infra/fin-infra/tests/test_cards_app.py` - Created test app (NEW FILE)

## Impact
- ✅ Banking capability now has landing page card with links to /banking/docs, /banking/redoc, /banking/openapi.json
- ✅ Market Data capability now has landing page card with links to /market/docs, /market/redoc, /market/openapi.json
- ✅ Pattern documented for all future capabilities
- ✅ Matches svc-infra's /auth, /payments, /admin card pattern
- ✅ Improved discoverability of fin-infra capabilities

## Next Steps for Future Capabilities
When adding new capabilities (brokerage, credit, tax), ensure `add_*()` helper includes:
1. Dual router from svc-infra (public_router, user_router, etc.)
2. `app.include_router(router, include_in_schema=True)`
3. **`add_prefixed_docs()` call immediately after mounting** ← Critical!
4. Store provider on `app.state`
5. Return provider instance

## Pattern Template
```python
def add_capability(app: FastAPI, provider=None, prefix="/capability") -> Provider:
    from svc_infra.api.fastapi.dual.public import public_router
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
    
    provider_instance = easy_capability(provider=provider)
    router = public_router(prefix=prefix, tags=["Capability"])
    
    # ... define routes ...
    
    app.include_router(router, include_in_schema=True)
    add_prefixed_docs(app, prefix=prefix, title="Capability", auto_exclude_from_root=True, visible_envs=None)
    app.state.capability_provider = provider_instance
    return provider_instance
```
