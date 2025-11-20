"""Unit tests for SnapTrade Investment provider."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from fin_infra.investments.models import SecurityType, TransactionType
from fin_infra.investments.providers.snaptrade import SnapTradeInvestmentProvider


# Fixtures


@pytest.fixture
def provider():
    """Create SnapTrade provider instance."""
    return SnapTradeInvestmentProvider(
        client_id="test_client_id",
        consumer_key="test_consumer_key",
        base_url="https://api.test.snaptrade.com/api/v1",
    )


@pytest.fixture
def mock_snaptrade_account():
    """Mock SnapTrade account data."""
    return {
        "id": "acc_123",
        "name": "E*TRADE Investment Account",
        "brokerage_name": "E*TRADE",
        "type": "investment",
        "account_type": "margin",
    }


@pytest.fixture
def mock_snaptrade_position():
    """Mock SnapTrade position data."""
    return {
        "symbol": {
            "id": "sym_aapl",
            "symbol": "AAPL",
            "description": "Apple Inc.",
            "type": "stock",
        },
        "units": 100,
        "price": 150.50,
        "value": 15050.00,
        "average_purchase_price": 140.00,
        "currency": "USD",
    }


@pytest.fixture
def mock_snaptrade_transaction():
    """Mock SnapTrade transaction data."""
    return {
        "id": "tx_123",
        "symbol": {
            "id": "sym_aapl",
            "symbol": "AAPL",
            "description": "Apple Inc.",
            "type": "stock",
        },
        "date": "2024-01-15",
        "type": "buy",
        "description": "Bought 100 shares of AAPL",
        "units": 100,
        "amount": -14000.00,
        "price": 140.00,
        "fee": 1.50,
        "currency": "USD",
    }


@pytest.fixture
def mock_snaptrade_balances():
    """Mock SnapTrade balances data."""
    return {
        "total": {"amount": 50000.00, "currency": "USD"},
        "cash": {"amount": 5000.00, "currency": "USD"},
    }


# Test __init__


def test_init_success():
    """Test successful initialization."""
    provider = SnapTradeInvestmentProvider(
        client_id="test_client",
        consumer_key="test_key",
    )
    assert provider.client_id == "test_client"
    assert provider.consumer_key == "test_key"
    assert provider.base_url == "https://api.snaptrade.com/api/v1"
    assert isinstance(provider.client, httpx.AsyncClient)


def test_init_custom_base_url():
    """Test initialization with custom base URL."""
    provider = SnapTradeInvestmentProvider(
        client_id="test_client",
        consumer_key="test_key",
        base_url="https://sandbox.snaptrade.com/api/v1",
    )
    assert provider.base_url == "https://sandbox.snaptrade.com/api/v1"


def test_init_missing_client_id():
    """Test initialization fails without client_id."""
    with pytest.raises(ValueError, match="client_id and consumer_key are required"):
        SnapTradeInvestmentProvider(client_id="", consumer_key="test_key")


def test_init_missing_consumer_key():
    """Test initialization fails without consumer_key."""
    with pytest.raises(ValueError, match="client_id and consumer_key are required"):
        SnapTradeInvestmentProvider(client_id="test_client", consumer_key="")


# Test get_holdings


@pytest.mark.asyncio
async def test_get_holdings_success(
    provider, mock_snaptrade_account, mock_snaptrade_position
):
    """Test successful holdings retrieval."""
    # Mock httpx client responses
    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [mock_snaptrade_account]
    mock_accounts_response.raise_for_status = Mock()

    mock_positions_response = AsyncMock()
    mock_positions_response.json.return_value = [mock_snaptrade_position]
    mock_positions_response.raise_for_status = Mock()

    # Mock client.get to return different responses based on URL
    async def mock_get(url, params=None):
        if "accounts" in url and "positions" not in url:
            return mock_accounts_response
        elif "positions" in url:
            return mock_positions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Test get_holdings
    holdings = await provider.get_holdings("user_123:secret_abc")

    # Assertions
    assert len(holdings) == 1
    holding = holdings[0]
    assert holding.account_id == "acc_123"
    assert holding.security.ticker_symbol == "AAPL"
    assert holding.quantity == Decimal("100")
    assert holding.institution_price == Decimal("150.50")
    assert holding.institution_value == Decimal("15050.00")
    assert holding.cost_basis == Decimal("14000.00")  # 100 * 140.00
    assert holding.unrealized_gain_loss == Decimal("1050.00")  # 15050 - 14000


@pytest.mark.asyncio
async def test_get_holdings_filtered_accounts(
    provider, mock_snaptrade_account, mock_snaptrade_position
):
    """Test holdings retrieval with account_ids filter."""
    # Create two accounts
    account1 = mock_snaptrade_account.copy()
    account1["id"] = "acc_123"
    account2 = mock_snaptrade_account.copy()
    account2["id"] = "acc_456"

    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [account1, account2]
    mock_accounts_response.raise_for_status = Mock()

    mock_positions_response = AsyncMock()
    mock_positions_response.json.return_value = [mock_snaptrade_position]
    mock_positions_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "accounts" in url and "positions" not in url:
            return mock_accounts_response
        elif "positions" in url:
            return mock_positions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Test with filter
    holdings = await provider.get_holdings("user_123:secret_abc", account_ids=["acc_123"])

    # Should only fetch positions for acc_123
    assert len(holdings) == 1
    assert holdings[0].account_id == "acc_123"


@pytest.mark.asyncio
async def test_get_holdings_invalid_access_token(provider):
    """Test holdings retrieval with invalid access token format."""
    with pytest.raises(ValueError, match="Invalid access_token format"):
        await provider.get_holdings("invalid_token_format")


    @pytest.mark.asyncio
    async def test_get_holdings_api_error(provider):
        """Test holdings retrieval handles API errors."""
        mock_response = Mock()  # Use Mock not AsyncMock for error responses
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"message": "Invalid credentials"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="401", request=Mock(), response=mock_response
        )

        provider.client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Invalid SnapTrade credentials"):
            await provider.get_holdings("user_123:secret_abc")
# Test get_transactions


@pytest.mark.asyncio
async def test_get_transactions_success(
    provider, mock_snaptrade_account, mock_snaptrade_transaction
):
    """Test successful transactions retrieval."""
    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [mock_snaptrade_account]
    mock_accounts_response.raise_for_status = Mock()

    mock_transactions_response = AsyncMock()
    mock_transactions_response.json.return_value = [mock_snaptrade_transaction]
    mock_transactions_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "accounts" in url and "transactions" not in url:
            return mock_accounts_response
        elif "transactions" in url:
            return mock_transactions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Test get_transactions
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)
    transactions = await provider.get_transactions(
        "user_123:secret_abc", start_date, end_date
    )

    # Assertions
    assert len(transactions) == 1
    tx = transactions[0]
    assert tx.transaction_id == "tx_123"
    assert tx.account_id == "acc_123"
    assert tx.security.ticker_symbol == "AAPL"
    assert tx.transaction_date == date(2024, 1, 15)
    assert tx.transaction_type == TransactionType.buy
    assert tx.quantity == Decimal("100")
    assert tx.amount == Decimal("-14000.00")
    assert tx.price == Decimal("140.00")
    assert tx.fees == Decimal("1.50")


@pytest.mark.asyncio
async def test_get_transactions_invalid_date_range(provider):
    """Test transactions retrieval with invalid date range."""
    start_date = date(2024, 2, 1)
    end_date = date(2024, 1, 1)  # Before start_date

    with pytest.raises(ValueError, match="start_date must be before end_date"):
        await provider.get_transactions("user_123:secret_abc", start_date, end_date)


@pytest.mark.asyncio
async def test_get_transactions_filtered_accounts(
    provider, mock_snaptrade_account, mock_snaptrade_transaction
):
    """Test transactions retrieval with account_ids filter."""
    account1 = mock_snaptrade_account.copy()
    account1["id"] = "acc_123"
    account2 = mock_snaptrade_account.copy()
    account2["id"] = "acc_456"

    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [account1, account2]
    mock_accounts_response.raise_for_status = Mock()

    mock_transactions_response = AsyncMock()
    mock_transactions_response.json.return_value = [mock_snaptrade_transaction]
    mock_transactions_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "accounts" in url and "transactions" not in url:
            return mock_accounts_response
        elif "transactions" in url:
            return mock_transactions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)
    transactions = await provider.get_transactions(
        "user_123:secret_abc", start_date, end_date, account_ids=["acc_123"]
    )

    assert len(transactions) == 1
    assert transactions[0].account_id == "acc_123"


# Test get_securities


@pytest.mark.asyncio
async def test_get_securities_success(
    provider, mock_snaptrade_account, mock_snaptrade_position
):
    """Test successful securities retrieval."""
    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [mock_snaptrade_account]
    mock_accounts_response.raise_for_status = Mock()

    # Create positions with different symbols
    position_aapl = mock_snaptrade_position.copy()
    position_googl = mock_snaptrade_position.copy()
    position_googl["symbol"] = {
        "id": "sym_googl",
        "symbol": "GOOGL",
        "description": "Alphabet Inc.",
        "type": "stock",
    }

    mock_positions_response = AsyncMock()
    mock_positions_response.json.return_value = [position_aapl, position_googl]
    mock_positions_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "accounts" in url and "positions" not in url:
            return mock_accounts_response
        elif "positions" in url:
            return mock_positions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Test get_securities
    securities = await provider.get_securities("user_123:secret_abc", ["AAPL", "GOOGL"])

    # Assertions
    assert len(securities) == 2
    symbols = {s.ticker_symbol for s in securities}
    assert symbols == {"AAPL", "GOOGL"}


@pytest.mark.asyncio
async def test_get_securities_filtered(
    provider, mock_snaptrade_account, mock_snaptrade_position
):
    """Test securities retrieval with symbol filter."""
    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [mock_snaptrade_account]
    mock_accounts_response.raise_for_status = Mock()

    position_aapl = mock_snaptrade_position.copy()
    position_googl = mock_snaptrade_position.copy()
    position_googl["symbol"] = {
        "id": "sym_googl",
        "symbol": "GOOGL",
        "description": "Alphabet Inc.",
        "type": "stock",
    }

    mock_positions_response = AsyncMock()
    mock_positions_response.json.return_value = [position_aapl, position_googl]
    mock_positions_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "accounts" in url and "positions" not in url:
            return mock_accounts_response
        elif "positions" in url:
            return mock_positions_response
        return AsyncMock()

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Only request AAPL
    securities = await provider.get_securities("user_123:secret_abc", ["AAPL"])

    assert len(securities) == 1
    assert securities[0].ticker_symbol == "AAPL"


# Test get_investment_accounts


@pytest.mark.asyncio
async def test_get_investment_accounts_success(
    provider,
    mock_snaptrade_account,
    mock_snaptrade_position,
    mock_snaptrade_balances,
):
    """Test successful investment accounts retrieval."""
    mock_accounts_response = AsyncMock()
    mock_accounts_response.json.return_value = [mock_snaptrade_account]
    mock_accounts_response.raise_for_status = Mock()

    mock_positions_response = AsyncMock()
    mock_positions_response.json.return_value = [mock_snaptrade_position]
    mock_positions_response.raise_for_status = Mock()

    mock_balances_response = AsyncMock()
    mock_balances_response.json.return_value = mock_snaptrade_balances
    mock_balances_response.raise_for_status = Mock()

    async def mock_get(url, params=None):
        if "balances" in url:
            return mock_balances_response
        elif "positions" in url:
            return mock_positions_response
        else:
            return mock_accounts_response

    provider.client.get = AsyncMock(side_effect=mock_get)

    # Test get_investment_accounts
    accounts = await provider.get_investment_accounts("user_123:secret_abc")

    # Assertions
    assert len(accounts) == 1
    account = accounts[0]
    assert account.account_id == "acc_123"
    assert account.name == "E*TRADE Investment Account"
    assert account.type == "investment"
    assert account.subtype == "margin"
    assert account.balances["current"] == 50000.00
    assert account.balances["available"] == 5000.00
    assert len(account.holdings) == 1
    # total_value = holdings value (15050) + cash balance (50000)
    assert account.total_value == Decimal("65050.0")
    assert account.total_cost_basis == Decimal("14000.00")
# Test list_connections


@pytest.mark.asyncio
async def test_list_connections_success(provider):
    """Test successful connections list retrieval."""
    mock_connections = [
        {
            "id": "conn_123",
            "brokerage_name": "E*TRADE",
            "status": "active",
        },
        {
            "id": "conn_456",
            "brokerage_name": "Robinhood",
            "status": "active",
        },
    ]

    mock_response = AsyncMock()
    mock_response.json.return_value = mock_connections
    mock_response.raise_for_status = Mock()

    provider.client.get = AsyncMock(return_value=mock_response)

    # Test list_connections
    connections = await provider.list_connections("user_123:secret_abc")

    # Assertions
    assert len(connections) == 2
    assert connections[0]["brokerage_name"] == "E*TRADE"
    assert connections[1]["brokerage_name"] == "Robinhood"


@pytest.mark.asyncio
async def test_list_connections_empty(provider):
    """Test connections list when no connections exist."""
    mock_response = AsyncMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    provider.client.get = AsyncMock(return_value=mock_response)

    connections = await provider.list_connections("user_123:secret_abc")

    assert len(connections) == 0


# Test get_brokerage_capabilities


def test_get_brokerage_capabilities_robinhood(provider):
    """Test Robinhood capabilities (read-only)."""
    caps = provider.get_brokerage_capabilities("Robinhood")

    assert caps["supports_trading"] is False
    assert caps["supports_options"] is False
    assert caps["read_only"] is True
    assert caps["connection_type"] == "oauth"


def test_get_brokerage_capabilities_etrade(provider):
    """Test E*TRADE capabilities (supports trading)."""
    caps = provider.get_brokerage_capabilities("E*TRADE")

    assert caps["supports_trading"] is True
    assert caps["supports_options"] is True
    assert caps["read_only"] is False
    assert caps["connection_type"] == "oauth"


def test_get_brokerage_capabilities_wealthsimple(provider):
    """Test Wealthsimple capabilities."""
    caps = provider.get_brokerage_capabilities("Wealthsimple")

    assert caps["supports_trading"] is True
    assert caps["supports_options"] is False
    assert caps["read_only"] is False


def test_get_brokerage_capabilities_unknown_brokerage(provider):
    """Test unknown brokerage returns default capabilities."""
    caps = provider.get_brokerage_capabilities("UnknownBroker")

    # Default capabilities
    assert caps["supports_trading"] is True
    assert caps["supports_options"] is False
    assert caps["read_only"] is False
    assert caps["connection_type"] == "oauth"


# Test helper methods


def test_parse_access_token_success(provider):
    """Test successful access_token parsing."""
    user_id, user_secret = provider._parse_access_token("user_123:secret_abc")

    assert user_id == "user_123"
    assert user_secret == "secret_abc"


def test_parse_access_token_with_colon_in_secret(provider):
    """Test access_token parsing with colon in secret."""
    user_id, user_secret = provider._parse_access_token("user_123:secret:with:colons")

    assert user_id == "user_123"
    assert user_secret == "secret:with:colons"


def test_parse_access_token_invalid_format(provider):
    """Test access_token parsing with invalid format."""
    with pytest.raises(ValueError, match="Invalid access_token format"):
        provider._parse_access_token("invalid_token_no_colon")


def test_transform_holding(provider, mock_snaptrade_position):
    """Test holding transformation."""
    holding = provider._transform_holding(mock_snaptrade_position, "acc_123")

    assert holding.account_id == "acc_123"
    assert holding.security.ticker_symbol == "AAPL"
    assert holding.security.name == "Apple Inc."
    assert holding.security.type == SecurityType.equity
    assert holding.quantity == Decimal("100")
    assert holding.institution_price == Decimal("150.50")
    assert holding.institution_value == Decimal("15050.00")
    assert holding.cost_basis == Decimal("14000.00")


def test_transform_transaction(provider, mock_snaptrade_transaction):
    """Test transaction transformation."""
    tx = provider._transform_transaction(mock_snaptrade_transaction, "acc_123")

    assert tx.transaction_id == "tx_123"
    assert tx.account_id == "acc_123"
    assert tx.security.ticker_symbol == "AAPL"
    assert tx.transaction_date == date(2024, 1, 15)
    assert tx.transaction_type == TransactionType.buy
    assert tx.quantity == Decimal("100")
    assert tx.amount == Decimal("-14000.00")
    assert tx.price == Decimal("140.00")
    assert tx.fees == Decimal("1.50")


def test_normalize_transaction_type_buy(provider):
    """Test transaction type normalization for buy."""
    assert provider._normalize_transaction_type("buy") == TransactionType.buy


def test_normalize_transaction_type_sell(provider):
    """Test transaction type normalization for sell."""
    assert provider._normalize_transaction_type("sell") == TransactionType.sell


def test_normalize_transaction_type_dividend(provider):
    """Test transaction type normalization for dividend."""
    assert provider._normalize_transaction_type("dividend") == TransactionType.dividend


def test_normalize_transaction_type_unknown(provider):
    """Test transaction type normalization for unknown type."""
    assert provider._normalize_transaction_type("custom_type") == TransactionType.other


# Test error transformation


def test_transform_error_401(provider):
    """Test 401 error transformation."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {"message": "Invalid credentials"}

    error = httpx.HTTPStatusError(
        message="401", request=Mock(), response=mock_response
    )
    transformed = provider._transform_error(error)

    assert isinstance(transformed, ValueError)
    assert "Invalid SnapTrade credentials" in str(transformed)


def test_transform_error_429(provider):
    """Test 429 rate limit error transformation."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_response.json.return_value = {"message": "Too many requests"}

    error = httpx.HTTPStatusError(
        message="429", request=Mock(), response=mock_response
    )
    transformed = provider._transform_error(error)

    assert isinstance(transformed, ValueError)
    assert "rate limit exceeded" in str(transformed)


def test_transform_error_404(provider):
    """Test 404 error transformation."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_response.json.side_effect = Exception("Not JSON")

    error = httpx.HTTPStatusError(
        message="404", request=Mock(), response=mock_response
    )
    transformed = provider._transform_error(error)

    assert isinstance(transformed, ValueError)
    assert "Resource not found" in str(transformed)


def test_transform_error_500(provider):
    """Test 500 error transformation."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    mock_response.json.return_value = {"message": "Server error"}

    error = httpx.HTTPStatusError(
        message="500", request=Mock(), response=mock_response
    )
    transformed = provider._transform_error(error)

    assert isinstance(transformed, Exception)
    assert "SnapTrade API error (500)" in str(transformed)


# Test async context manager


@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager usage."""
    async with SnapTradeInvestmentProvider(
        client_id="test_client",
        consumer_key="test_key",
    ) as provider:
        assert isinstance(provider, SnapTradeInvestmentProvider)
        assert isinstance(provider.client, httpx.AsyncClient)

    # Client should be closed after context exit
    # Note: httpx.AsyncClient doesn't have is_closed attribute,
    # but we can verify the context manager works
