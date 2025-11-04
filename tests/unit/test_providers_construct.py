from fin_infra.providers.market.yahoo import YahooFinanceMarketData
from fin_infra.providers.market.ccxt_crypto import CCXTCryptoData


def test_providers_construct():
    y = YahooFinanceMarketData()
    assert y is not None
    c = CCXTCryptoData("binance")
    assert c is not None
