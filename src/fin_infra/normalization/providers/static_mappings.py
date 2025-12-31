"""Static symbol mappings for common tickers (reduces API calls)."""

# Top 50 US stocks by market cap (2024)
TICKER_TO_CUSIP = {
    "AAPL": "037833100",  # Apple Inc.
    "MSFT": "594918104",  # Microsoft Corporation
    "GOOGL": "02079K305",  # Alphabet Inc. Class A
    "GOOG": "02079K107",  # Alphabet Inc. Class C
    "AMZN": "023135106",  # Amazon.com Inc.
    "NVDA": "67066G104",  # NVIDIA Corporation
    "TSLA": "88160R101",  # Tesla Inc.
    "META": "30303M102",  # Meta Platforms Inc.
    "BRK.B": "084670702",  # Berkshire Hathaway Inc. Class B
    "UNH": "91324P102",  # UnitedHealth Group Inc.
    "XOM": "30231G102",  # Exxon Mobil Corporation
    "JNJ": "478160104",  # Johnson & Johnson
    "JPM": "46625H100",  # JPMorgan Chase & Co.
    "V": "92826C839",  # Visa Inc.
    "PG": "742718109",  # Procter & Gamble Company
    "MA": "57636Q104",  # Mastercard Inc.
    "HD": "437076102",  # Home Depot Inc.
    "CVX": "166764100",  # Chevron Corporation
    "MRK": "58933Y105",  # Merck & Co. Inc.
    "ABBV": "00287Y109",  # AbbVie Inc.
    "KO": "191216100",  # Coca-Cola Company
    "PEP": "713448108",  # PepsiCo Inc.
    "AVGO": "11135F101",  # Broadcom Inc.
    "COST": "22160K105",  # Costco Wholesale Corporation
    "TMO": "883556102",  # Thermo Fisher Scientific Inc.
    "WMT": "931142103",  # Walmart Inc.
    "NFLX": "64110L106",  # Netflix Inc.
    "DIS": "254687106",  # Walt Disney Company
    "ABT": "002824100",  # Abbott Laboratories
    "CSCO": "17275R102",  # Cisco Systems Inc.
    "ACN": "G1151C101",  # Accenture plc
    "ORCL": "68389X105",  # Oracle Corporation
    "NKE": "654106103",  # NIKE Inc.
    "CRM": "79466L302",  # Salesforce Inc.
    "ADBE": "00724F101",  # Adobe Inc.
    "TXN": "882508104",  # Texas Instruments Inc.
    "INTC": "458140100",  # Intel Corporation
    "VZ": "92343V104",  # Verizon Communications Inc.
    "AMD": "007903107",  # Advanced Micro Devices Inc.
    "CMCSA": "20030N101",  # Comcast Corporation Class A
    "QCOM": "747525103",  # QUALCOMM Inc.
    "IBM": "459200101",  # International Business Machines Corp.
    "BA": "097023105",  # Boeing Company
    "GE": "369604301",  # General Electric Company
    "CAT": "149123101",  # Caterpillar Inc.
    "GS": "38141G104",  # Goldman Sachs Group Inc.
    "MS": "617446448",  # Morgan Stanley
    "BAC": "060505104",  # Bank of America Corporation
    "WFC": "949746101",  # Wells Fargo & Company
    "C": "172967424",  # Citigroup Inc.
}

# Convert CUSIP to ISIN (US prefix + CUSIP + checksum)
TICKER_TO_ISIN = {
    "AAPL": "US0378331005",
    "MSFT": "US5949181045",
    "GOOGL": "US02079K3059",
    "GOOG": "US02079K1079",
    "AMZN": "US0231351067",
    "NVDA": "US67066G1040",
    "TSLA": "US88160R1014",
    "META": "US30303M1027",
    "BRK.B": "US0846707026",
    "UNH": "US91324P1021",
    "XOM": "US30231G1022",
    "JNJ": "US4781601046",
    "JPM": "US46625H1005",
    "V": "US92826C8394",
    "PG": "US7427181091",
    "MA": "US57636Q1040",
    "HD": "US4370761029",
    "CVX": "US1667641005",
    "MRK": "US58933Y1055",
    "ABBV": "US00287Y1091",
    "KO": "US1912161007",
    "PEP": "US7134481081",
    "AVGO": "US11135F1012",
    "COST": "US22160K1051",
    "TMO": "US8835561023",
    "WMT": "US9311421039",
    "NFLX": "US64110L1061",
    "DIS": "US2546871060",
    "ABT": "US0028241000",
    "CSCO": "US17275R1023",
    "ACN": "IE00B4BNMY34",  # Ireland-based
    "ORCL": "US68389X1054",
    "NKE": "US6541061031",
    "CRM": "US79466L3024",
    "ADBE": "US00724F1012",
    "TXN": "US8825081040",
    "INTC": "US4581401001",
    "VZ": "US92343V1044",
    "AMD": "US0079031078",
    "CMCSA": "US20030N1019",
    "QCOM": "US7475251036",
    "IBM": "US4592001014",
    "BA": "US0970231058",
    "GE": "US3696043013",
    "CAT": "US1491231015",
    "GS": "US38141G1040",
    "MS": "US6174464486",
    "BAC": "US0605051046",
    "WFC": "US9497461015",
    "C": "US1729674242",
}

# Provider-specific symbol normalization
# Maps provider-specific format -> standard ticker
PROVIDER_SYMBOL_MAP = {
    "yahoo": {
        # Yahoo Finance uses dashes for crypto
        "BTC-USD": "BTC",
        "ETH-USD": "ETH",
        "BNB-USD": "BNB",
        "XRP-USD": "XRP",
        "ADA-USD": "ADA",
        "DOGE-USD": "DOGE",
        "SOL-USD": "SOL",
        "DOT-USD": "DOT",
        "MATIC-USD": "MATIC",
        "LTC-USD": "LTC",
    },
    "coingecko": {
        # CoinGecko uses full names
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "binancecoin": "BNB",
        "ripple": "XRP",
        "cardano": "ADA",
        "dogecoin": "DOGE",
        "solana": "SOL",
        "polkadot": "DOT",
        "polygon": "MATIC",
        "litecoin": "LTC",
    },
    "alpaca": {
        # Alpaca uses no separators for crypto
        "BTCUSD": "BTC",
        "ETHUSD": "ETH",
        "BNBUSD": "BNB",
        "XRPUSD": "XRP",
        "ADAUSD": "ADA",
        "DOGEUSD": "DOGE",
        "SOLUSD": "SOL",
        "DOTUSD": "DOT",
        "MATICUSD": "MATIC",
        "LTCUSD": "LTC",
    },
    "alphavantage": {
        # Alpha Vantage standard format
        # (no special mappings needed for stocks)
    },
    "plaid": {
        # Plaid uses account IDs, not tickers
        # (normalization done at banking layer)
    },
}

# Reverse mappings for efficiency
CUSIP_TO_TICKER = {v: k for k, v in TICKER_TO_CUSIP.items()}
ISIN_TO_TICKER = {v: k for k, v in TICKER_TO_ISIN.items()}


# Company metadata for cached symbols
TICKER_METADATA = {
    "AAPL": {
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "asset_type": "stock",
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Software",
        "asset_type": "stock",
    },
    "GOOGL": {
        "name": "Alphabet Inc. Class A",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Internet Services",
        "asset_type": "stock",
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "exchange": "NASDAQ",
        "sector": "Consumer Cyclical",
        "industry": "E-commerce",
        "asset_type": "stock",
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "exchange": "NASDAQ",
        "sector": "Consumer Cyclical",
        "industry": "Automotive",
        "asset_type": "stock",
    },
    "BTC": {
        "name": "Bitcoin",
        "exchange": "CRYPTO",
        "sector": "Cryptocurrency",
        "industry": "Digital Currency",
        "asset_type": "crypto",
    },
    "ETH": {
        "name": "Ethereum",
        "exchange": "CRYPTO",
        "sector": "Cryptocurrency",
        "industry": "Smart Contract Platform",
        "asset_type": "crypto",
    },
}
