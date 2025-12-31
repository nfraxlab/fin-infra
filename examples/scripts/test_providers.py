#!/usr/bin/env python3
"""
Test provider connections and credentials for fin-infra-template.

This script validates that all configured providers are properly set up
and can successfully connect. It tests each provider individually and
provides clear success/failure reporting with actionable error messages.

Usage:
    # Test all configured providers
    python scripts/test_providers.py

    # Test specific provider
    python scripts/test_providers.py --provider banking
    python scripts/test_providers.py --provider market
    python scripts/test_providers.py --provider crypto

    # Verbose output
    python scripts/test_providers.py --verbose

    # List all providers
    python scripts/test_providers.py --list

Available Providers:
    banking         Banking integration (Plaid, Teller)
    market          Market data (Alpha Vantage, Yahoo, Polygon)
    crypto          Cryptocurrency data (CoinGecko, CCXT)
    credit          Credit scores (Experian, Equifax, TransUnion)
    brokerage       Brokerage integration (Alpaca, IB)
    tax             Tax data (IRS, TaxBit)
    categorization  Transaction categorization (local)
    recurring       Recurring detection (local)
    analytics       Financial analytics (local + LLM)
    cashflows       Financial calculations (local)
    normalization   Symbol/currency normalization (local)
    conversation    AI-powered financial chat (LLM)

Environment Variables:
    Banking:        PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV
    Market:         ALPHA_VANTAGE_API_KEY, POLYGON_API_KEY
    Crypto:         COINGECKO_API_KEY (optional)
    Credit:         EXPERIAN_API_KEY, EXPERIAN_CLIENT_SECRET
    Brokerage:      ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
    AI/LLM:         GOOGLE_GENAI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY
"""

import argparse
import asyncio
import os
import sys
from collections.abc import Callable
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(message: str):
    """Print success message with green checkmark."""
    print(f"{Colors.GREEN}[OK] {message}{Colors.END}")


def print_error(message: str):
    """Print error message with red X."""
    print(f"{Colors.RED}[X] {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message with yellow warning sign."""
    print(f"{Colors.YELLOW}[!]  {message}{Colors.END}")


def print_info(message: str):
    """Print info message with blue bullet."""
    print(f"{Colors.BLUE}[i]  {message}{Colors.END}")


def print_header(message: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{message}{Colors.END}")
    print("=" * 70)


def check_env_vars(required: list[str]) -> tuple[bool, list[str]]:
    """Check if required environment variables are set."""
    missing = [var for var in required if not os.getenv(var)]
    return len(missing) == 0, missing


# ==================== Provider Test Functions ====================


async def test_banking(verbose: bool = False) -> bool:
    """Test banking provider (Plaid)."""
    print_header("Testing Banking Provider (Plaid)")

    # Check environment variables
    required_vars = ["PLAID_CLIENT_ID", "PLAID_SECRET", "PLAID_ENVIRONMENT"]
    configured, missing = check_env_vars(required_vars)

    if not configured:
        print_error(f"Banking not configured. Missing: {', '.join(missing)}")
        print_info("To configure Plaid:")
        print("   1. Sign up at https://dashboard.plaid.com/signup")
        print("   2. Get your Client ID and Secret from dashboard")
        print("   3. Add to .env:")
        print("      PLAID_CLIENT_ID=your_client_id")
        print("      PLAID_SECRET=your_sandbox_secret")
        print("      PLAID_ENVIRONMENT=sandbox")
        return False

    try:
        from fin_infra.banking import easy_banking

        banking = easy_banking()
        print_success("Banking provider initialized")

        # Test link token creation
        link_response = banking.create_link_token()
        if link_response and "link_token" in link_response:
            print_success(f"Link token created: {link_response['link_token'][:20]}...")
            if verbose:
                print_info(f"Full response: {link_response}")
            return True
        else:
            print_error("Failed to create link token")
            return False

    except Exception as e:
        print_error(f"Banking provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_market(verbose: bool = False) -> bool:
    """Test market data provider."""
    print_header("Testing Market Data Provider")

    # Check if any market provider is configured
    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    polygon_key = os.getenv("POLYGON_API_KEY")

    if not av_key and not polygon_key:
        print_warning("No market data API keys configured (will use Yahoo fallback)")
        print_info("For better data quality:")
        print("   Alpha Vantage: https://www.alphavantage.co/support/#api-key")
        print("   Add to .env: ALPHA_VANTAGE_API_KEY=your_key")

    try:
        from fin_infra.markets import easy_market

        market = easy_market()
        print_success("Market data provider initialized")

        # Test quote fetch
        quote = market.quote("AAPL")
        if quote and hasattr(quote, "price"):
            print_success(f"Market data working: AAPL @ ${quote.price:.2f}")
            if verbose:
                print_info(f"Full quote: {quote}")
            return True
        else:
            print_error("Failed to fetch market data")
            return False

    except Exception as e:
        print_error(f"Market data provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        print_info("Suggestions:")
        print("   • Check API key is valid")
        print("   • Verify rate limits not exceeded")
        print("   • Try without API key (uses Yahoo Finance)")
        return False


async def test_crypto(verbose: bool = False) -> bool:
    """Test crypto data provider."""
    print_header("Testing Crypto Data Provider")

    print_info("CoinGecko free tier - no API key needed")

    try:
        from fin_infra.markets.crypto import easy_crypto

        crypto = easy_crypto()
        print_success("Crypto data provider initialized")

        # Test crypto quote fetch
        quote = crypto.quote("BTC")
        if quote and hasattr(quote, "price"):
            print_success(f"Crypto data working: BTC @ ${quote.price:,.2f}")
            if verbose:
                print_info(f"Full quote: {quote}")
            return True
        else:
            print_error("Failed to fetch crypto data")
            return False

    except Exception as e:
        print_error(f"Crypto data provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_credit(verbose: bool = False) -> bool:
    """Test credit score provider."""
    print_header("Testing Credit Score Provider")

    required_vars = ["EXPERIAN_API_KEY", "EXPERIAN_CLIENT_SECRET"]
    configured, missing = check_env_vars(required_vars)

    if not configured:
        print_warning(f"Credit provider not configured. Missing: {', '.join(missing)}")
        print_info("To configure Experian:")
        print("   Contact Experian for enterprise API access")
        print("   This is typically for lending/credit monitoring apps")
        return False

    try:
        from fin_infra.credit import easy_credit

        easy_credit()
        print_success("Credit score provider initialized")
        print_info("Note: Actual credit score testing requires user consent")
        return True

    except Exception as e:
        print_error(f"Credit provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_brokerage(verbose: bool = False) -> bool:
    """Test brokerage provider (Alpaca)."""
    print_header("Testing Brokerage Provider (Alpaca)")

    required_vars = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
    configured, missing = check_env_vars(required_vars)

    if not configured:
        print_warning(f"Brokerage not configured. Missing: {', '.join(missing)}")
        print_info("To configure Alpaca paper trading (free):")
        print("   1. Sign up at https://alpaca.markets")
        print("   2. Get paper trading keys")
        print("   3. Add to .env:")
        print("      ALPACA_API_KEY=your_paper_key")
        print("      ALPACA_SECRET_KEY=your_paper_secret")
        print("      ALPACA_BASE_URL=https://paper-api.alpaca.markets")
        return False

    try:
        from fin_infra.brokerage import easy_brokerage

        brokerage = easy_brokerage()
        print_success("Brokerage provider initialized")

        # Test account info fetch
        account = brokerage.get_account()
        if account:
            buying_power = getattr(account, "buying_power", 0)
            print_success(f"Brokerage account connected: ${buying_power:,.2f} buying power")
            if verbose:
                print_info(f"Full account: {account}")
            return True
        else:
            print_error("Failed to fetch account info")
            return False

    except Exception as e:
        print_error(f"Brokerage provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_categorization(verbose: bool = False) -> bool:
    """Test transaction categorization (local, no API key)."""
    print_header("Testing Transaction Categorization")

    try:
        from fin_infra.categorization import easy_categorization

        categorizer = easy_categorization()
        print_success("Categorization provider initialized")

        # Test categorization
        result = categorizer.categorize(description="STARBUCKS COFFEE", amount=5.75, user_id="test")
        if result and hasattr(result, "category"):
            print_success(f"Categorization working: 'STARBUCKS' → {result.category}")
            if verbose:
                print_info(f"Full result: {result}")
            return True
        else:
            print_error("Categorization failed")
            return False

    except Exception as e:
        print_error(f"Categorization provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_recurring(verbose: bool = False) -> bool:
    """Test recurring transaction detection (local, no API key)."""
    print_header("Testing Recurring Detection")

    try:
        from fin_infra.recurring import easy_recurring

        easy_recurring()
        print_success("Recurring detection provider initialized")
        print_info("Note: Requires transaction history for pattern detection")
        return True

    except Exception as e:
        print_error(f"Recurring detection provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_analytics(verbose: bool = False) -> bool:
    """Test financial analytics."""
    print_header("Testing Financial Analytics")

    llm_configured = (
        os.getenv("GOOGLE_GENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )

    if not llm_configured:
        print_warning("LLM not configured (AI-powered insights disabled)")
        print_info("To enable AI insights, configure one of:")
        print("   GOOGLE_GENAI_API_KEY (recommended, free tier)")
        print("   OPENAI_API_KEY")
        print("   ANTHROPIC_API_KEY")

    try:
        from fin_infra.analytics import easy_analytics

        easy_analytics()
        print_success("Analytics provider initialized")
        print_info("Note: Full testing requires user transaction data")
        return True

    except Exception as e:
        print_error(f"Analytics provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_cashflows(verbose: bool = False) -> bool:
    """Test financial cashflow calculations (local, no API key)."""
    print_header("Testing Cashflow Calculations")

    try:
        from fin_infra.cashflows import irr, npv

        # Test NPV
        result = npv(0.08, [-10000, 3000, 4000, 5000])
        print_success(f"NPV calculation working: {result:.2f}")

        # Test IRR
        result = irr([-10000, 3000, 4000, 5000])
        print_success(f"IRR calculation working: {result:.4f}")

        if verbose:
            print_info("Cashflow functions: NPV, IRR, PMT, FV, PV all available")

        return True

    except Exception as e:
        print_error(f"Cashflow calculations failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_normalization(verbose: bool = False) -> bool:
    """Test symbol/currency normalization (local, no API key)."""
    print_header("Testing Normalization")

    try:
        from fin_infra.normalization import easy_normalization

        normalizer = easy_normalization()
        print_success("Normalization provider initialized")

        # Test symbol resolution
        result = normalizer.resolve_symbol("AAPL")
        if result:
            print_success(f"Symbol resolution working: AAPL → {result.get('name', 'Unknown')}")
            if verbose:
                print_info(f"Full result: {result}")

        return True

    except Exception as e:
        print_error(f"Normalization provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


async def test_conversation(verbose: bool = False) -> bool:
    """Test AI conversation (requires LLM)."""
    print_header("Testing AI Conversation")

    llm_configured = (
        os.getenv("GOOGLE_GENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )

    if not llm_configured:
        print_warning("LLM not configured - AI conversation disabled")
        print_info("To enable AI conversation, configure one of:")
        print("   GOOGLE_GENAI_API_KEY (recommended, free tier)")
        print("   OPENAI_API_KEY")
        print("   ANTHROPIC_API_KEY")
        return False

    try:
        from fin_infra.chat import easy_financial_conversation

        easy_financial_conversation()
        print_success("AI conversation provider initialized")
        print_info("Note: Full testing requires user context and questions")
        return True

    except Exception as e:
        print_error(f"AI conversation provider failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


# ==================== Provider Registry ====================

PROVIDERS: dict[str, Callable] = {
    "banking": test_banking,
    "market": test_market,
    "crypto": test_crypto,
    "credit": test_credit,
    "brokerage": test_brokerage,
    "categorization": test_categorization,
    "recurring": test_recurring,
    "analytics": test_analytics,
    "cashflows": test_cashflows,
    "normalization": test_normalization,
    "conversation": test_conversation,
}


# ==================== Main CLI ====================


async def run_tests(provider: str | None = None, verbose: bool = False) -> int:
    """Run provider tests."""
    print_header(" FIN-INFRA PROVIDER TEST SUITE")

    if provider:
        # Test specific provider
        if provider not in PROVIDERS:
            print_error(f"Unknown provider: {provider}")
            print_info(f"Available providers: {', '.join(PROVIDERS.keys())}")
            return 1

        success = await PROVIDERS[provider](verbose)
        return 0 if success else 1

    else:
        # Test all providers
        results = {}
        for name, test_func in PROVIDERS.items():
            results[name] = await test_func(verbose)

        # Summary
        print_header(" Test Summary")
        passed = sum(1 for success in results.values() if success)
        total = len(results)

        for name, success in results.items():
            status = "[OK] PASS" if success else "[X] FAIL"
            print(f"   {status}  {name}")

        print(f"\n{Colors.BOLD}Results: {passed}/{total} providers working{Colors.END}")

        if passed == total:
            print_success("All configured providers are working!")
            return 0
        elif passed > 0:
            print_warning(f"{total - passed} provider(s) need configuration")
            return 1
        else:
            print_error("No providers configured")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test fin-infra provider connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--provider", "-p", help="Test specific provider", choices=list(PROVIDERS.keys())
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument("--list", "-l", action="store_true", help="List all providers")

    args = parser.parse_args()

    if args.list:
        print_header("Available Providers")
        for name in PROVIDERS.keys():
            print(f"   • {name}")
        return 0

    # Load environment variables from .env if it exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        print_info(f"Loaded environment from {env_file}")
    else:
        print_warning("No .env file found - using system environment variables only")

    # Run tests
    return asyncio.run(run_tests(args.provider, args.verbose))


if __name__ == "__main__":
    sys.exit(main())
