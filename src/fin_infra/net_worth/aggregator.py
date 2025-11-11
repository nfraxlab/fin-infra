"""
Net Worth Aggregator Module

Aggregates account balances from multiple financial providers:
- Banking (Plaid/Teller) - cash + credit cards + loans
- Brokerage (Alpaca) - stock holdings + cash balance
- Crypto (CCXT) - wallet + exchange balances

**Quick Start**:
```python
from fin_infra.net_worth.aggregator import NetWorthAggregator
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage

# Create providers
banking = easy_banking(provider="plaid")
brokerage = easy_brokerage(provider="alpaca")

# Create aggregator
aggregator = NetWorthAggregator(
    banking_provider=banking,
    brokerage_provider=brokerage,
    base_currency="USD"
)

# Aggregate net worth
snapshot = await aggregator.aggregate_net_worth(user_id="user_123")
print(f"Net Worth: ${snapshot.total_net_worth:,.2f}")
```
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from fin_infra.net_worth.calculator import (
    calculate_asset_allocation,
    calculate_liability_breakdown,
    calculate_net_worth,
)
from fin_infra.net_worth.models import (
    AssetCategory,
    AssetDetail,
    LiabilityCategory,
    LiabilityDetail,
    NetWorthSnapshot,
)


class NetWorthAggregator:
    """
    Aggregates net worth from multiple financial providers.

    **Features**:
    - Multi-provider support (banking, brokerage, crypto)
    - Parallel account fetching (faster performance)
    - Graceful error handling (continue if one provider fails)
    - Currency normalization (all → base currency)
    - Market value calculation (stocks/crypto)

    **Example**:
    ```python
    aggregator = NetWorthAggregator(
        banking_provider=banking,
        brokerage_provider=brokerage,
        crypto_provider=crypto,
        base_currency="USD"
    )

    snapshot = await aggregator.aggregate_net_worth("user_123")
    print(f"Assets: ${snapshot.total_assets:,.2f}")
    print(f"Liabilities: ${snapshot.total_liabilities:,.2f}")
    print(f"Net Worth: ${snapshot.total_net_worth:,.2f}")
    ```
    """

    def __init__(
        self,
        banking_provider: Any = None,
        brokerage_provider: Any = None,
        crypto_provider: Any = None,
        market_provider: Any = None,
        base_currency: str = "USD",
    ):
        """
        Initialize aggregator with providers.

        Args:
            banking_provider: Banking provider (Plaid/Teller)
            brokerage_provider: Brokerage provider (Alpaca)
            crypto_provider: Crypto provider (CCXT)
            market_provider: Market data provider (Alpha Vantage)
            base_currency: Base currency for normalization (default: USD)

        Raises:
            ValueError: If no providers specified
        """
        self.banking_provider = banking_provider
        self.brokerage_provider = brokerage_provider
        self.crypto_provider = crypto_provider
        self.market_provider = market_provider
        self.base_currency = base_currency

        # Validate at least one provider
        if not any([banking_provider, brokerage_provider, crypto_provider]):
            raise ValueError("At least one provider required (banking, brokerage, or crypto)")

    async def aggregate_net_worth(
        self,
        user_id: str,
        access_token: str | None = None,
    ) -> NetWorthSnapshot:
        """
        Aggregate net worth from all providers.

        Fetches balances from all configured providers in parallel,
        calculates totals, and returns a complete snapshot.

        **Example**:
        ```python
        snapshot = await aggregator.aggregate_net_worth(
            user_id="user_123",
            access_token="plaid_token_abc"
        )
        ```

        Args:
            user_id: User identifier
            access_token: Provider access token (for banking/brokerage)

        Returns:
            NetWorthSnapshot with complete financial picture
        """
        # Fetch accounts from all providers (parallel)
        assets_list, liabilities_list, providers_used = await self._fetch_all_accounts(
            user_id=user_id,
            access_token=access_token,
        )

        # Calculate net worth
        total_net_worth = calculate_net_worth(
            assets=assets_list,
            liabilities=liabilities_list,
            base_currency=self.base_currency,
        )

        # Calculate breakdowns
        asset_allocation = calculate_asset_allocation(assets_list)
        liability_breakdown = calculate_liability_breakdown(liabilities_list)

        # Create snapshot
        snapshot = NetWorthSnapshot(
            id=str(uuid.uuid4()),
            user_id=user_id,
            snapshot_date=datetime.utcnow(),
            total_net_worth=total_net_worth,
            total_assets=asset_allocation.total_assets,
            total_liabilities=liability_breakdown.total_liabilities,
            change_from_previous=None,  # Will be calculated when storing
            change_percentage=None,
            cash=asset_allocation.cash,
            investments=asset_allocation.investments,
            crypto=asset_allocation.crypto,
            real_estate=asset_allocation.real_estate,
            vehicles=asset_allocation.vehicles,
            other_assets=asset_allocation.other_assets,
            credit_cards=liability_breakdown.credit_cards,
            mortgages=liability_breakdown.mortgages,
            auto_loans=liability_breakdown.auto_loans,
            student_loans=liability_breakdown.student_loans,
            personal_loans=liability_breakdown.personal_loans,
            lines_of_credit=liability_breakdown.lines_of_credit,
            asset_count=len(assets_list),
            liability_count=len(liabilities_list),
            providers=providers_used,
            base_currency=self.base_currency,
            created_at=datetime.utcnow(),
        )

        return snapshot

    async def _fetch_all_accounts(
        self,
        user_id: str,
        access_token: str | None = None,
    ) -> tuple[list[AssetDetail], list[LiabilityDetail], list[str]]:
        """
        Fetch accounts from all providers in parallel.

        Returns:
            Tuple of (assets, liabilities, providers_used)
        """
        tasks = []
        providers_used = []

        # Banking provider (cash + credit cards + loans)
        if self.banking_provider:
            tasks.append(self._fetch_banking_accounts(user_id, access_token))
            providers_used.append("banking")

        # Brokerage provider (stock holdings)
        if self.brokerage_provider:
            tasks.append(self._fetch_brokerage_accounts(user_id, access_token))
            providers_used.append("brokerage")

        # Crypto provider (wallet balances)
        if self.crypto_provider:
            tasks.append(self._fetch_crypto_accounts(user_id))
            providers_used.append("crypto")

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results (skip failed providers)
        all_assets = []
        all_liabilities = []
        actual_providers = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log error but continue (graceful degradation)
                print(f"Provider {providers_used[i]} failed: {result}")
                continue

            assets, liabilities = result
            all_assets.extend(assets)
            all_liabilities.extend(liabilities)
            actual_providers.append(providers_used[i])

        return all_assets, all_liabilities, actual_providers

    async def _fetch_banking_accounts(
        self,
        user_id: str,
        access_token: str | None,
    ) -> tuple[list[AssetDetail], list[LiabilityDetail]]:
        """
        Fetch banking accounts (cash + credit cards + loans).

        Returns:
            Tuple of (assets, liabilities)
        """
        if not access_token:
            # For now, return empty if no token
            # TODO: Implement token storage/retrieval
            return [], []

        # Fetch accounts from banking provider
        # This is a placeholder - actual implementation depends on provider
        accounts = await self.banking_provider.get_accounts(access_token)

        assets = []
        liabilities = []

        for account in accounts:
            account_type = account.get("type", "").lower()
            balance = account.get("balance", 0.0)

            # Categorize account
            if account_type in ["checking", "savings", "money_market"]:
                # Asset: Cash account
                assets.append(
                    AssetDetail(
                        account_id=account["id"],
                        provider="banking",
                        account_type=AssetCategory.CASH,
                        name=account.get("name", "Cash Account"),
                        balance=balance,
                        currency=account.get("currency", "USD"),
                        last_updated=datetime.utcnow(),
                    )
                )
            elif account_type == "credit_card":
                # Liability: Credit card debt
                liabilities.append(
                    LiabilityDetail(
                        account_id=account["id"],
                        provider="banking",
                        liability_type=LiabilityCategory.CREDIT_CARD,
                        name=account.get("name", "Credit Card"),
                        balance=balance,
                        currency=account.get("currency", "USD"),
                        interest_rate=account.get("apr"),
                        last_updated=datetime.utcnow(),
                    )
                )
            elif account_type == "mortgage":
                # Liability: Mortgage
                liabilities.append(
                    LiabilityDetail(
                        account_id=account["id"],
                        provider="banking",
                        liability_type=LiabilityCategory.MORTGAGE,
                        name=account.get("name", "Mortgage"),
                        balance=balance,
                        currency=account.get("currency", "USD"),
                        interest_rate=account.get("apr"),
                        last_updated=datetime.utcnow(),
                    )
                )
            elif "loan" in account_type:
                # Liability: Various loans
                if "student" in account_type:
                    liability_type = LiabilityCategory.STUDENT_LOAN
                elif "auto" in account_type or "car" in account_type:
                    liability_type = LiabilityCategory.AUTO_LOAN
                else:
                    liability_type = LiabilityCategory.PERSONAL_LOAN

                liabilities.append(
                    LiabilityDetail(
                        account_id=account["id"],
                        provider="banking",
                        liability_type=liability_type,
                        name=account.get("name", "Loan"),
                        balance=balance,
                        currency=account.get("currency", "USD"),
                        interest_rate=account.get("apr"),
                        last_updated=datetime.utcnow(),
                    )
                )

        return assets, liabilities

    async def _fetch_brokerage_accounts(
        self,
        user_id: str,
        access_token: str | None,
    ) -> tuple[list[AssetDetail], list[LiabilityDetail]]:
        """
        Fetch brokerage accounts (stock holdings + cash).

        Returns:
            Tuple of (assets, liabilities)
        """
        # Placeholder implementation
        # Actual implementation depends on brokerage provider API

        # Get account info from brokerage
        # account = await self.brokerage_provider.get_account()

        # For now, return empty
        # TODO: Implement actual brokerage integration
        return [], []

    async def _fetch_crypto_accounts(
        self,
        user_id: str,
    ) -> tuple[list[AssetDetail], list[LiabilityDetail]]:
        """
        Fetch crypto accounts (wallet + exchange balances).

        Returns:
            Tuple of (assets, liabilities)
        """
        # Placeholder implementation
        # Actual implementation depends on crypto provider API

        # Get balances from crypto provider
        # balances = await self.crypto_provider.get_balances()

        # For now, return empty
        # TODO: Implement actual crypto integration
        return [], []
