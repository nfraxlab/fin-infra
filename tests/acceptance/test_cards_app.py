"""Test app to verify landing page cards for banking and market data."""

import os

import pytest

# Skip entire module if Teller certificates not available
TELLER_CERT = os.getenv("TELLER_CERT_PATH")
TELLER_KEY = os.getenv("TELLER_KEY_PATH")
if (
    not TELLER_CERT
    or not TELLER_KEY
    or not os.path.exists(TELLER_CERT)
    or not os.path.exists(TELLER_KEY)
):
    pytest.skip(
        "Teller certificates not available - skipping cards app tests", allow_module_level=True
    )

from svc_infra.api.fastapi.ease import easy_service_app  # noqa: E402

from fin_infra.banking import add_banking  # noqa: E402
from fin_infra.markets import add_market_data  # noqa: E402

# Create app
app = easy_service_app(name="FinInfraTest", release="test")

# Add banking capability (should create card at /)
banking = add_banking(app, provider="teller")

# Add market data capability (should create card at /)
market = add_market_data(app, provider="yahoo")

if __name__ == "__main__":
    import uvicorn

    print("\n Starting test server...")
    print(" Landing page with cards: http://localhost:8000/")
    print(" Banking docs: http://localhost:8000/banking/docs")
    print(" Market docs: http://localhost:8000/market/docs")
    print("\n[OK] Expected cards on landing page: Banking, Market Data")
    uvicorn.run(app, host="0.0.0.0", port=8000)
