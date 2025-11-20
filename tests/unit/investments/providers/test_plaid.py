"""Unit tests for PlaidInvestmentProvider with mocked Plaid API."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from fin_infra.investments.models import (
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
    SecurityType,
    TransactionType,
)
from fin_infra.investments.providers.plaid import PlaidInvestmentProvider


@pytest.fixture
def provider():
    """Create PlaidInvestmentProvider instance."""
    with patch("fin_infra.investments.providers.plaid.ApiClient"):
        with patch("fin_infra.investments.providers.plaid.plaid_api.PlaidApi"):
            provider = PlaidInvestmentProvider(
                client_id="test_client_id",
                secret="test_secret",
                environment="sandbox",
            )
            return provider


@pytest.fixture
def mock_plaid_security():
    """Create mock Plaid security response."""
    security = Mock()
    security.security_id = "sec_aapl_123"
    security.to_dict.return_value = {
        "security_id": "sec_aapl_123",
        "cusip": "037833100",
        "isin": "US0378331005",
        "sedol": None,
        "ticker_symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "equity",
        "sector": "Technology",
        "close_price": 175.50,
        "close_price_as_of": "2025-11-20",
        "market_identifier_code": "XNAS",
        "iso_currency_code": "USD",
    }
    return security


@pytest.fixture
def mock_plaid_holding(mock_plaid_security):
    """Create mock Plaid holding response."""
    holding = Mock()
    holding.to_dict.return_value = {
        "account_id": "acc_401k_123",
        "security_id": "sec_aapl_123",
        "quantity": 10.0,
        "institution_price": 175.50,
        "institution_value": 1755.00,
        "cost_basis": 1500.00,
        "iso_currency_code": "USD",
        "unofficial_currency_code": None,
    }
    return holding


@pytest.fixture
def mock_plaid_transaction(mock_plaid_security):
    """Create mock Plaid investment transaction response."""
    transaction = Mock()
    transaction.to_dict.return_value = {
        "investment_transaction_id": "tx_buy_123",
        "account_id": "acc_401k_123",
        "security_id": "sec_aapl_123",
        "date": "2025-11-15",
        "name": "Buy AAPL",
        "type": "buy",
        "subtype": None,
        "quantity": 10.0,
        "amount": 1755.00,
        "price": 175.50,
        "fees": 0.00,
        "iso_currency_code": "USD",
        "unofficial_currency_code": None,
    }
    return transaction


@pytest.fixture
def mock_plaid_account():
    """Create mock Plaid account response."""
    account = Mock()
    account.account_id = "acc_401k_123"
    account.to_dict.return_value = {
        "account_id": "acc_401k_123",
        "name": "401(k) Account",
        "official_name": "Vanguard 401(k)",
        "type": "investment",
        "subtype": "401k",
        "balances": {
            "current": 1755.00,
            "available": 1755.00,
        },
    }
    return account


# Tests for __init__


class TestInit:
    """Tests for PlaidInvestmentProvider initialization."""

    def test_init_success(self):
        """Test successful initialization with valid credentials."""
        with patch("fin_infra.investments.providers.plaid.ApiClient"):
            with patch("fin_infra.investments.providers.plaid.plaid_api.PlaidApi"):
                provider = PlaidInvestmentProvider(
                    client_id="test_client",
                    secret="test_secret",
                    environment="sandbox",
                )
                assert provider.client_id == "test_client"
                assert provider.secret == "test_secret"
                assert provider.environment == "sandbox"

    def test_init_missing_credentials(self):
        """Test initialization fails with missing credentials."""
        with pytest.raises(ValueError, match="client_id and secret are required"):
            PlaidInvestmentProvider(client_id="", secret="", environment="sandbox")

    def test_init_default_environment(self):
        """Test initialization with default sandbox environment."""
        with patch("fin_infra.investments.providers.plaid.ApiClient"):
            with patch("fin_infra.investments.providers.plaid.plaid_api.PlaidApi"):
                provider = PlaidInvestmentProvider(
                    client_id="test_client",
                    secret="test_secret",
                )
                assert provider.environment == "sandbox"


# Tests for get_holdings


class TestGetHoldings:
    """Tests for get_holdings method."""

    @pytest.mark.asyncio
    async def test_get_holdings_success(
        self, provider, mock_plaid_security, mock_plaid_holding
    ):
        """Test successful holdings retrieval."""
        # Mock Plaid API response
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]
        mock_response.holdings = [mock_plaid_holding]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Call method
        holdings = await provider.get_holdings("access_token_123")

        # Assertions
        assert len(holdings) == 1
        holding = holdings[0]
        assert isinstance(holding, Holding)
        assert holding.account_id == "acc_401k_123"
        assert holding.security.ticker_symbol == "AAPL"
        assert holding.quantity == Decimal("10.0")
        assert holding.institution_price == Decimal("175.50")
        assert holding.institution_value == Decimal("1755.00")
        assert holding.cost_basis == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_get_holdings_with_account_filter(
        self, provider, mock_plaid_security, mock_plaid_holding
    ):
        """Test holdings retrieval with account ID filter."""
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]
        mock_response.holdings = [mock_plaid_holding]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Call with account filter
        holdings = await provider.get_holdings(
            "access_token_123", account_ids=["acc_401k_123"]
        )

        # Verify request was made with account filter
        call_args = provider.client.investments_holdings_get.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_holdings_empty(self, provider):
        """Test holdings retrieval with no holdings."""
        mock_response = Mock()
        mock_response.securities = []
        mock_response.holdings = []

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        holdings = await provider.get_holdings("access_token_123")

        assert holdings == []

    @pytest.mark.asyncio
    async def test_get_holdings_api_error(self, provider):
        """Test holdings retrieval with API error."""
        from plaid.exceptions import ApiException

        error = ApiException(status=401, reason="Unauthorized")
        error.error_code = "INVALID_ACCESS_TOKEN"
        error.display_message = "Invalid access token"

        provider.client.investments_holdings_get = Mock(side_effect=error)

        with pytest.raises(ValueError, match="Invalid Plaid access token"):
            await provider.get_holdings("invalid_token")


# Tests for get_transactions


class TestGetTransactions:
    """Tests for get_transactions method."""

    @pytest.mark.asyncio
    async def test_get_transactions_success(
        self, provider, mock_plaid_security, mock_plaid_transaction
    ):
        """Test successful transactions retrieval."""
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]
        mock_response.investment_transactions = [mock_plaid_transaction]

        provider.client.investments_transactions_get = Mock(return_value=mock_response)

        # Call method
        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 20)
        transactions = await provider.get_transactions(
            "access_token_123", start_date, end_date
        )

        # Assertions
        assert len(transactions) == 1
        tx = transactions[0]
        assert isinstance(tx, InvestmentTransaction)
        assert tx.transaction_id == "tx_buy_123"
        assert tx.account_id == "acc_401k_123"
        assert tx.security.ticker_symbol == "AAPL"
        assert tx.transaction_type == TransactionType.buy
        assert tx.quantity == Decimal("10.0")
        assert tx.amount == Decimal("1755.00")
        assert tx.price == Decimal("175.50")

    @pytest.mark.asyncio
    async def test_get_transactions_with_account_filter(
        self, provider, mock_plaid_security, mock_plaid_transaction
    ):
        """Test transactions retrieval with account filter."""
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]
        mock_response.investment_transactions = [mock_plaid_transaction]

        provider.client.investments_transactions_get = Mock(return_value=mock_response)

        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 20)
        transactions = await provider.get_transactions(
            "access_token_123", start_date, end_date, account_ids=["acc_401k_123"]
        )

        assert len(transactions) == 1

    @pytest.mark.asyncio
    async def test_get_transactions_invalid_date_range(self, provider):
        """Test transactions retrieval with invalid date range."""
        start_date = date(2025, 11, 20)
        end_date = date(2025, 11, 1)  # End before start

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            await provider.get_transactions("access_token_123", start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_transactions_empty(self, provider):
        """Test transactions retrieval with no transactions."""
        mock_response = Mock()
        mock_response.securities = []
        mock_response.investment_transactions = []

        provider.client.investments_transactions_get = Mock(return_value=mock_response)

        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 20)
        transactions = await provider.get_transactions(
            "access_token_123", start_date, end_date
        )

        assert transactions == []


# Tests for get_securities


class TestGetSecurities:
    """Tests for get_securities method."""

    @pytest.mark.asyncio
    async def test_get_securities_success(self, provider, mock_plaid_security):
        """Test successful securities retrieval."""
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Call method
        securities = await provider.get_securities(
            "access_token_123", ["sec_aapl_123"]
        )

        # Assertions
        assert len(securities) == 1
        security = securities[0]
        assert isinstance(security, Security)
        assert security.security_id == "sec_aapl_123"
        assert security.ticker_symbol == "AAPL"
        assert security.name == "Apple Inc."
        assert security.type == SecurityType.equity
        assert security.sector == "Technology"
        assert security.close_price == Decimal("175.50")

    @pytest.mark.asyncio
    async def test_get_securities_filter(self, provider):
        """Test securities retrieval filters by requested IDs."""
        # Create multiple securities
        sec1 = Mock()
        sec1.security_id = "sec_aapl_123"
        sec1.to_dict.return_value = {
            "security_id": "sec_aapl_123",
            "ticker_symbol": "AAPL",
            "name": "Apple Inc.",
            "type": "equity",
            "close_price": 175.50,
            "iso_currency_code": "USD",
        }

        sec2 = Mock()
        sec2.security_id = "sec_googl_456"
        sec2.to_dict.return_value = {
            "security_id": "sec_googl_456",
            "ticker_symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "type": "equity",
            "close_price": 140.00,
            "iso_currency_code": "USD",
        }

        mock_response = Mock()
        mock_response.securities = [sec1, sec2]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Request only AAPL
        securities = await provider.get_securities(
            "access_token_123", ["sec_aapl_123"]
        )

        # Should only return AAPL
        assert len(securities) == 1
        assert securities[0].ticker_symbol == "AAPL"


# Tests for get_investment_accounts


class TestGetInvestmentAccounts:
    """Tests for get_investment_accounts method."""

    @pytest.mark.asyncio
    async def test_get_investment_accounts_success(
        self,
        provider,
        mock_plaid_security,
        mock_plaid_holding,
        mock_plaid_account,
    ):
        """Test successful investment accounts retrieval."""
        mock_response = Mock()
        mock_response.securities = [mock_plaid_security]
        mock_response.holdings = [mock_plaid_holding]
        mock_response.accounts = [mock_plaid_account]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Call method
        accounts = await provider.get_investment_accounts("access_token_123")

        # Assertions
        assert len(accounts) == 1
        account = accounts[0]
        assert isinstance(account, InvestmentAccount)
        assert account.account_id == "acc_401k_123"
        assert account.name == "401(k) Account"
        assert account.type == "investment"
        assert account.subtype == "401k"
        assert len(account.holdings) == 1
        assert account.holdings[0].security.ticker_symbol == "AAPL"

        # Check computed fields work
        assert account.total_value > 0
        assert account.total_cost_basis > 0

    @pytest.mark.asyncio
    async def test_get_investment_accounts_multiple_holdings(
        self, provider, mock_plaid_account
    ):
        """Test account with multiple holdings."""
        # Create multiple securities and holdings
        sec1 = Mock()
        sec1.security_id = "sec_aapl_123"
        sec1.to_dict.return_value = {
            "security_id": "sec_aapl_123",
            "ticker_symbol": "AAPL",
            "name": "Apple Inc.",
            "type": "equity",
            "close_price": 175.50,
            "iso_currency_code": "USD",
        }

        sec2 = Mock()
        sec2.security_id = "sec_googl_456"
        sec2.to_dict.return_value = {
            "security_id": "sec_googl_456",
            "ticker_symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "type": "equity",
            "close_price": 140.00,
            "iso_currency_code": "USD",
        }

        holding1 = Mock()
        holding1.to_dict.return_value = {
            "account_id": "acc_401k_123",
            "security_id": "sec_aapl_123",
            "quantity": 10.0,
            "institution_price": 175.50,
            "institution_value": 1755.00,
            "cost_basis": 1500.00,
            "iso_currency_code": "USD",
        }

        holding2 = Mock()
        holding2.to_dict.return_value = {
            "account_id": "acc_401k_123",
            "security_id": "sec_googl_456",
            "quantity": 5.0,
            "institution_price": 140.00,
            "institution_value": 700.00,
            "cost_basis": 650.00,
            "iso_currency_code": "USD",
        }

        mock_response = Mock()
        mock_response.securities = [sec1, sec2]
        mock_response.holdings = [holding1, holding2]
        mock_response.accounts = [mock_plaid_account]

        provider.client.investments_holdings_get = Mock(return_value=mock_response)

        # Call method
        accounts = await provider.get_investment_accounts("access_token_123")

        # Assertions
        assert len(accounts) == 1
        account = accounts[0]
        assert len(account.holdings) == 2
        # total_value = balance.current (1755) + holdings (1755 + 700) = 4210
        assert account.total_value == Decimal("4210.0")


# Tests for helper methods


class TestHelperMethods:
    """Tests for transformation and helper methods."""

    def test_transform_security(self, provider, mock_plaid_security):
        """Test security transformation."""
        plaid_dict = mock_plaid_security.to_dict()
        security = provider._transform_security(plaid_dict)

        assert isinstance(security, Security)
        assert security.security_id == "sec_aapl_123"
        assert security.ticker_symbol == "AAPL"
        assert security.type == SecurityType.equity

    def test_transform_holding(self, provider, mock_plaid_holding):
        """Test holding transformation."""
        plaid_dict = mock_plaid_holding.to_dict()
        security = Security(
            security_id="sec_aapl_123",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
            close_price=Decimal("175.50"),
            currency="USD",
        )

        holding = provider._transform_holding(plaid_dict, security)

        assert isinstance(holding, Holding)
        assert holding.account_id == "acc_401k_123"
        assert holding.quantity == Decimal("10.0")
        assert holding.institution_value == Decimal("1755.00")

    def test_transform_transaction(self, provider, mock_plaid_transaction):
        """Test transaction transformation."""
        plaid_dict = mock_plaid_transaction.to_dict()
        security = Security(
            security_id="sec_aapl_123",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
            close_price=Decimal("175.50"),
            currency="USD",
        )

        transaction = provider._transform_transaction(plaid_dict, security)

        assert isinstance(transaction, InvestmentTransaction)
        assert transaction.transaction_id == "tx_buy_123"
        assert transaction.transaction_type == TransactionType.buy
        assert transaction.quantity == Decimal("10.0")

    def test_normalize_transaction_type(self, provider):
        """Test transaction type normalization."""
        assert provider._normalize_transaction_type("buy") == TransactionType.buy
        assert provider._normalize_transaction_type("sell") == TransactionType.sell
        assert provider._normalize_transaction_type("dividend") == TransactionType.dividend
        assert provider._normalize_transaction_type("unknown") == TransactionType.other

    def test_transform_error_invalid_token(self, provider):
        """Test error transformation for invalid token."""
        from plaid.exceptions import ApiException

        error = ApiException(status=401, reason="Unauthorized")
        error.error_code = "INVALID_ACCESS_TOKEN"
        error.display_message = "Invalid access token"

        transformed = provider._transform_error(error)

        assert isinstance(transformed, ValueError)
        assert "Invalid Plaid access token" in str(transformed)

    def test_transform_error_rate_limit(self, provider):
        """Test error transformation for rate limit."""
        from plaid.exceptions import ApiException

        error = ApiException(status=429, reason="Too Many Requests")
        error.error_code = "RATE_LIMIT_EXCEEDED"
        error.display_message = "Rate limit exceeded"

        transformed = provider._transform_error(error)

        assert isinstance(transformed, ValueError)
        assert "rate limit exceeded" in str(transformed)

    def test_transform_error_generic(self, provider):
        """Test error transformation for generic error."""
        from plaid.exceptions import ApiException

        error = ApiException(status=500, reason="Internal Server Error")
        error.error_code = "INTERNAL_SERVER_ERROR"
        error.display_message = "Something went wrong"

        transformed = provider._transform_error(error)

        assert isinstance(transformed, Exception)
        assert "Plaid API error" in str(transformed)
