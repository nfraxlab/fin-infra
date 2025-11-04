from fin_infra.providers.market.alphavantage import AlphaVantageMarketData
from fin_infra.providers.market.coingecko import CoinGeckoCryptoData
from fin_infra.providers.banking.teller_client import TellerClient
from fin_infra.providers.identity.stripe_identity import StripeIdentity
from fin_infra.providers.credit.experian import ExperianCredit


def test_default_providers_construct():
    """Test that providers can be constructed with minimal required params."""
    # AlphaVantage requires API key (pass test key)
    assert AlphaVantageMarketData(api_key="test_key") is not None
    
    # These don't require API keys for construction
    assert CoinGeckoCryptoData() is not None
    assert TellerClient() is not None
    assert StripeIdentity() is not None
    assert ExperianCredit() is not None
