"""Benchmarks for cashflow calculations.

Run with:
    make benchmark
    pytest benchmarks/bench_cashflows.py --benchmark-only
"""

from __future__ import annotations


class TestCashflowsImport:
    """Benchmark cashflows module imports."""

    def test_cashflows_import(self, benchmark):
        """Benchmark cashflows module import time."""

        def import_cashflows():
            import importlib

            import fin_infra.cashflows

            importlib.reload(fin_infra.cashflows)

        benchmark(import_cashflows)


class TestNPVCalculations:
    """Benchmark NPV calculations."""

    def test_npv_small(self, benchmark):
        """Benchmark NPV with small cashflow series."""
        from fin_infra.cashflows import npv

        cashflows = [-10000, 3000, 4000, 5000]

        result = benchmark(npv, 0.08, cashflows)
        assert result > 0

    def test_npv_medium(self, benchmark, sample_cashflows):
        """Benchmark NPV with medium cashflow series (30 periods)."""
        from fin_infra.cashflows import npv

        result = benchmark(npv, 0.08, sample_cashflows)
        assert isinstance(result, float)

    def test_npv_large(self, benchmark):
        """Benchmark NPV with large cashflow series (360 months = 30 years)."""
        from fin_infra.cashflows import npv

        # Monthly cashflows for 30 years
        cashflows = [-500000] + [2000] * 360

        result = benchmark(npv, 0.005, cashflows)  # ~6% annual rate
        assert isinstance(result, float)


class TestIRRCalculations:
    """Benchmark IRR calculations."""

    def test_irr_small(self, benchmark):
        """Benchmark IRR with small cashflow series."""
        from fin_infra.cashflows import irr

        cashflows = [-10000, 3000, 4000, 5000]

        result = benchmark(irr, cashflows)
        assert 0 < result < 1

    def test_irr_medium(self, benchmark, sample_cashflows):
        """Benchmark IRR with medium cashflow series."""
        from fin_infra.cashflows import irr

        result = benchmark(irr, sample_cashflows)
        assert isinstance(result, float)

    def test_irr_large(self, benchmark):
        """Benchmark IRR with large cashflow series (120 months = 10 years)."""
        from fin_infra.cashflows import irr

        # 10-year investment with monthly returns
        cashflows = [-100000] + [1200] * 119 + [1200 + 100000]

        result = benchmark(irr, cashflows)
        assert isinstance(result, float)


class TestPMTCalculations:
    """Benchmark loan payment calculations."""

    def test_pmt_mortgage(self, benchmark, sample_loan_params):
        """Benchmark mortgage payment calculation."""
        from fin_infra.cashflows import pmt

        rate = sample_loan_params["rate"]
        nper = sample_loan_params["nper"]
        pv = sample_loan_params["pv"]

        result = benchmark(pmt, rate, nper, pv)
        assert result < 0  # Payment is an outflow


class TestFVCalculations:
    """Benchmark future value calculations."""

    def test_fv_savings(self, benchmark):
        """Benchmark FV for retirement savings."""
        from fin_infra.cashflows import fv

        # 30 years of $500/month at 7% annual
        rate = 0.07 / 12
        nper = 30 * 12
        payment = -500

        result = benchmark(fv, rate, nper, payment)
        assert result > 0


class TestPVCalculations:
    """Benchmark present value calculations."""

    def test_pv_annuity(self, benchmark):
        """Benchmark PV for annuity."""
        from fin_infra.cashflows import pv

        # What's the present value of $1000/month for 20 years at 5%?
        rate = 0.05 / 12
        nper = 20 * 12
        payment = -1000

        result = benchmark(pv, rate, nper, payment)
        assert result > 0
