import os
import pytest

from fin_infra.providers.banking.teller_client import TellerClient


pytestmark = [pytest.mark.acceptance]


@pytest.mark.skipif(
    not (os.getenv("TELLER_CERTIFICATE_PATH") and os.getenv("TELLER_PRIVATE_KEY_PATH")),
    reason="No Teller certificates configured (set TELLER_CERTIFICATE_PATH and TELLER_PRIVATE_KEY_PATH)",
)
def test_teller_accounts_smoke():
    """Smoke test for Teller banking provider with real certificates."""
    cert_path = os.getenv("TELLER_CERTIFICATE_PATH")
    key_path = os.getenv("TELLER_PRIVATE_KEY_PATH")
    environment = os.getenv("TELLER_ENVIRONMENT", "sandbox")

    teller = TellerClient(cert_path=cert_path, key_path=key_path, environment=environment)

    # Verify all required methods exist
    assert hasattr(teller, "create_link_token")
    assert hasattr(teller, "exchange_public_token")
    assert hasattr(teller, "accounts")
    assert hasattr(teller, "transactions")
    assert hasattr(teller, "balances")
    assert hasattr(teller, "identity")

    # Verify client is properly initialized
    assert teller.cert_path == cert_path
    assert teller.key_path == key_path
    assert teller.environment == environment
    assert teller.base_url == "https://api.sandbox.teller.io"
