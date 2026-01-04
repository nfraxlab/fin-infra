"""Benchmarks for transaction categorization.

Run with:
    make benchmark
    pytest benchmarks/bench_categorization.py --benchmark-only
"""

from __future__ import annotations


class TestCategorizationImport:
    """Benchmark categorization module imports."""

    def test_categorization_import(self, benchmark):
        """Benchmark categorization module import time."""

        def import_categorization():
            import importlib

            import fin_infra.categorization

            importlib.reload(fin_infra.categorization)

        benchmark(import_categorization)


class TestTaxonomy:
    """Benchmark taxonomy operations."""

    def test_get_all_categories(self, benchmark):
        """Benchmark loading all categories."""
        from fin_infra.categorization import get_all_categories

        result = benchmark(get_all_categories)
        assert len(result) > 0

    def test_get_category_group(self, benchmark):
        """Benchmark category group lookup."""
        from fin_infra.categorization import get_category_group

        def lookup_group():
            return get_category_group("Coffee Shops")

        result = benchmark(lookup_group)
        assert result is not None


class TestEngineInit:
    """Benchmark CategorizationEngine initialization."""

    def test_engine_init_basic(self, benchmark):
        """Benchmark basic engine initialization (no ML/LLM)."""
        from fin_infra.categorization import CategorizationEngine

        def create_engine():
            return CategorizationEngine(
                enable_ml=False,
                enable_llm=False,
            )

        result = benchmark(create_engine)
        assert result is not None

    def test_engine_init_with_ml(self, benchmark):
        """Benchmark engine initialization with ML enabled."""
        from fin_infra.categorization import CategorizationEngine

        def create_engine():
            return CategorizationEngine(
                enable_ml=True,
                enable_llm=False,
            )

        result = benchmark(create_engine)
        assert result is not None


class TestEasyCategorization:
    """Benchmark easy_categorization factory."""

    def test_easy_categorization_rules_only(self, benchmark):
        """Benchmark easy_categorization with rules-only model."""
        from fin_infra.categorization import easy_categorization

        def create_categorizer():
            return easy_categorization(model="rules")

        result = benchmark(create_categorizer)
        assert result is not None

    def test_easy_categorization_hybrid(self, benchmark):
        """Benchmark easy_categorization with hybrid model."""
        from fin_infra.categorization import easy_categorization

        def create_categorizer():
            return easy_categorization(model="hybrid", enable_ml=True)

        result = benchmark(create_categorizer)
        assert result is not None


class TestCategorizationModels:
    """Benchmark model/request creation."""

    def test_request_creation(self, benchmark, sample_transactions):
        """Benchmark CategorizationRequest creation."""
        from fin_infra.categorization import CategorizationRequest

        def create_requests():
            return [
                CategorizationRequest(description=txn["description"]) for txn in sample_transactions
            ]

        result = benchmark(create_requests)
        assert len(result) == len(sample_transactions)

    def test_prediction_creation(self, benchmark):
        """Benchmark CategoryPrediction creation."""
        from fin_infra.categorization import CategoryPrediction

        def create_prediction():
            return CategoryPrediction(
                category="Coffee Shops",
                confidence=0.95,
                method="exact",
            )

        result = benchmark(create_prediction)
        assert result.category == "Coffee Shops"
