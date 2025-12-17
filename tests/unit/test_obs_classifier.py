"""
Tests for financial route classifier.

Verifies that financial routes are correctly classified without
hardcoding specific endpoints.
"""

import pytest

from fin_infra.obs.classifier import (
    FINANCIAL_ROUTE_PREFIXES,
    compose_classifiers,
    financial_route_classifier,
)


class TestFinancialRouteClassifier:
    """Test financial route classification logic."""

    def test_banking_routes_classified_as_financial(self):
        """Banking routes should be classified as financial."""
        assert financial_route_classifier("/banking/accounts", "GET") == "financial"
        assert financial_route_classifier("/banking/accounts/{id}", "GET") == "financial"
        assert financial_route_classifier("/banking/transactions", "GET") == "financial"
        assert financial_route_classifier("/banking/balances/{id}", "POST") == "financial"

    def test_market_routes_classified_as_financial(self):
        """Market data routes should be classified as financial."""
        assert financial_route_classifier("/market/quote/{symbol}", "GET") == "financial"
        assert financial_route_classifier("/market/quotes", "GET") == "financial"
        assert financial_route_classifier("/market/search", "GET") == "financial"

    def test_crypto_routes_classified_as_financial(self):
        """Crypto routes should be classified as financial."""
        assert financial_route_classifier("/crypto/price/{symbol}", "GET") == "financial"
        assert financial_route_classifier("/crypto/tickers", "GET") == "financial"

    def test_brokerage_routes_classified_as_financial(self):
        """Brokerage routes should be classified as financial."""
        assert financial_route_classifier("/brokerage/account", "GET") == "financial"
        assert financial_route_classifier("/brokerage/positions", "GET") == "financial"
        assert financial_route_classifier("/brokerage/orders", "POST") == "financial"

    def test_credit_routes_classified_as_financial(self):
        """Credit score routes should be classified as financial."""
        assert financial_route_classifier("/credit/score", "GET") == "financial"
        assert financial_route_classifier("/credit/report", "GET") == "financial"

    def test_tax_routes_classified_as_financial(self):
        """Tax data routes should be classified as financial."""
        assert financial_route_classifier("/tax/documents", "GET") == "financial"
        assert financial_route_classifier("/tax/forms/{year}", "GET") == "financial"

    def test_all_financial_prefixes_detected(self):
        """Verify all defined financial prefixes are classified correctly."""
        for prefix in FINANCIAL_ROUTE_PREFIXES:
            # Test exact prefix
            assert financial_route_classifier(prefix, "GET") == "financial"
            # Test with path continuation
            assert financial_route_classifier(f"{prefix}/subpath", "GET") == "financial"
            # Test with parameters
            assert financial_route_classifier(f"{prefix}/{{id}}", "GET") == "financial"

    def test_non_financial_routes_classified_as_public(self):
        """Non-financial routes should be classified as public."""
        assert financial_route_classifier("/health", "GET") == "public"
        assert financial_route_classifier("/healthz", "GET") == "public"
        assert financial_route_classifier("/metrics", "GET") == "public"
        assert financial_route_classifier("/docs", "GET") == "public"
        assert financial_route_classifier("/openapi.json", "GET") == "public"
        assert financial_route_classifier("/", "GET") == "public"

    def test_root_path_classified_as_public(self):
        """Root path should be classified as public."""
        assert financial_route_classifier("/", "GET") == "public"

    def test_trailing_slash_normalized(self):
        """Trailing slashes should be normalized for consistent classification."""
        assert financial_route_classifier("/banking/", "GET") == "financial"
        assert financial_route_classifier("/banking", "GET") == "financial"
        assert financial_route_classifier("/health/", "GET") == "public"
        assert financial_route_classifier("/health", "GET") == "public"

    def test_method_parameter_accepted(self):
        """Classifier should accept method parameter (for future use)."""
        # Currently method isn't used in classification, but the interface requires it
        assert financial_route_classifier("/banking/accounts", "GET") == "financial"
        assert financial_route_classifier("/banking/accounts", "POST") == "financial"
        assert financial_route_classifier("/banking/accounts", "PUT") == "financial"
        assert financial_route_classifier("/banking/accounts", "DELETE") == "financial"

    def test_case_sensitive_classification(self):
        """Classification should be case-sensitive (FastAPI routes are lowercase)."""
        # Financial routes are lowercase by convention
        assert financial_route_classifier("/banking/accounts", "GET") == "financial"
        # Mixed case should not match (FastAPI normalizes to lowercase)
        assert financial_route_classifier("/Banking/Accounts", "GET") == "public"
        assert financial_route_classifier("/BANKING/ACCOUNTS", "GET") == "public"

    def test_non_matching_prefixes_are_public(self):
        """Routes that don't match any financial prefix should be public."""
        # These don't start with any financial prefix
        assert financial_route_classifier("/bank", "GET") == "public"  # not /banking
        assert financial_route_classifier("/broker", "GET") == "public"  # not /brokerage
        assert financial_route_classifier("/user", "GET") == "public"
        assert financial_route_classifier("/settings", "GET") == "public"
        assert financial_route_classifier("/api/v1/data", "GET") == "public"


class TestComposeClassifiers:
    """Test classifier composition helper."""

    def test_compose_with_custom_admin_classifier(self):
        """Should compose financial classifier with admin classifier."""

        def admin_classifier(path: str, method: str) -> str:
            if path.startswith("/admin"):
                return "admin"
            return "public"

        composed = compose_classifiers(
            financial_route_classifier,
            admin_classifier,
            default="public",
        )

        # Financial routes should be classified as financial
        assert composed("/banking/accounts", "GET") == "financial"
        assert composed("/market/quote/AAPL", "GET") == "financial"

        # Admin routes should be classified as admin
        assert composed("/admin/users", "GET") == "admin"
        assert composed("/admin/settings", "POST") == "admin"

        # Other routes should be public
        assert composed("/health", "GET") == "public"
        assert composed("/docs", "GET") == "public"

    def test_compose_order_matters(self):
        """First matching classifier should win."""

        def override_classifier(path: str, method: str) -> str:
            if path.startswith("/banking"):
                return "overridden"
            return "public"

        # Override first - banking routes become "overridden"
        composed1 = compose_classifiers(
            override_classifier,
            financial_route_classifier,
            default="public",
        )
        assert composed1("/banking/accounts", "GET") == "overridden"

        # Financial first - banking routes become "financial"
        composed2 = compose_classifiers(
            financial_route_classifier,
            override_classifier,
            default="public",
        )
        assert composed2("/banking/accounts", "GET") == "financial"

    def test_compose_with_three_classifiers(self):
        """Should support composing multiple classifiers."""

        def admin_classifier(path: str, method: str) -> str:
            return "admin" if path.startswith("/admin") else "public"

        def internal_classifier(path: str, method: str) -> str:
            return "internal" if path.startswith("/internal") else "public"

        composed = compose_classifiers(
            financial_route_classifier,
            admin_classifier,
            internal_classifier,
            default="public",
        )

        assert composed("/banking/accounts", "GET") == "financial"
        assert composed("/admin/users", "GET") == "admin"
        assert composed("/internal/debug", "GET") == "internal"
        assert composed("/health", "GET") == "public"

    def test_compose_fallback_to_default(self):
        """Should return default when no classifier matches."""

        def never_match(path: str, method: str) -> str:
            return "public"

        composed = compose_classifiers(
            never_match,
            default="public",
        )

        assert composed("/anything", "GET") == "public"


class TestFinancialRoutePrefixes:
    """Test that financial route prefix list is comprehensive."""

    def test_all_expected_prefixes_present(self):
        """Verify all expected financial prefixes are defined."""
        expected = [
            "/banking",
            "/market",
            "/crypto",
            "/brokerage",
            "/credit",
            "/tax",
            "/cashflow",
            "/transaction",
            "/portfolio",
            "/wallet",
        ]

        for prefix in expected:
            assert prefix in FINANCIAL_ROUTE_PREFIXES, (
                f"Expected financial prefix {prefix} not found"
            )

    def test_prefixes_are_lowercase(self):
        """All prefixes should be lowercase (FastAPI convention)."""
        for prefix in FINANCIAL_ROUTE_PREFIXES:
            assert prefix == prefix.lower(), f"Prefix {prefix} should be lowercase"

    def test_prefixes_start_with_slash(self):
        """All prefixes should start with / for proper route matching."""
        for prefix in FINANCIAL_ROUTE_PREFIXES:
            assert prefix.startswith("/"), f"Prefix {prefix} should start with /"

    def test_prefixes_no_trailing_slash(self):
        """Prefixes should not have trailing slash (normalized in classifier)."""
        for prefix in FINANCIAL_ROUTE_PREFIXES:
            assert not prefix.endswith("/"), f"Prefix {prefix} should not end with /"


class TestIntegrationWithSvcInfra:
    """Test integration patterns with svc-infra."""

    def test_classifier_signature_matches_protocol(self):
        """Classifier should match svc-infra's RouteClassifier protocol."""
        # Protocol: def __call__(self, route_path: str, method: str) -> str
        result = financial_route_classifier("/banking/accounts", "GET")
        assert isinstance(result, str)

    def test_can_be_used_with_add_observability(self):
        """Verify classifier can be passed to add_observability."""
        # This is a smoke test - actual integration tested in acceptance tests
        try:
            from svc_infra.obs import add_observability

            # Should not raise - just verify the signature is compatible
            # (Don't actually call add_observability without an app)
            assert callable(financial_route_classifier)
            assert callable(add_observability)
        except ImportError:
            pytest.skip("svc-infra not installed")
