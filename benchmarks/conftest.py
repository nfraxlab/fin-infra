"""Benchmark fixtures and configuration for fin-infra."""

from __future__ import annotations

import random

import pytest


@pytest.fixture
def sample_cashflows() -> list[float]:
    """Sample cashflows for NPV/IRR benchmarks."""
    return [-100000.0] + [random.uniform(10000, 30000) for _ in range(10)]


@pytest.fixture
def sample_loan_params() -> dict:
    """Sample loan parameters for PMT benchmarks."""
    return {
        "rate": 0.05 / 12,  # 5% annual, monthly
        "nper": 360,  # 30 years
        "pv": 300000,  # $300k loan
    }


@pytest.fixture
def sample_transactions() -> list[dict]:
    """Sample transactions for categorization benchmarks."""
    return [
        {"merchant": "Amazon", "description": "AMAZON.COM*123456 SEATTLE WA", "amount": 50.0},
        {"merchant": "Starbucks", "description": "STARBUCKS #12345 NEW YORK NY", "amount": 5.50},
        {"merchant": "Uber", "description": "UBER TRIP HELP.UBER.COM", "amount": 25.00},
        {"merchant": "Spotify", "description": "SPOTIFY USA", "amount": 9.99},
        {"merchant": "Whole Foods", "description": "WHOLE FOODS MARKET #10234", "amount": 85.00},
        {"merchant": "Shell", "description": "SHELL OIL 12345678901", "amount": 45.00},
        {"merchant": "Target", "description": "TARGET 00012345 CHICAGO IL", "amount": 120.00},
        {"merchant": "Netflix", "description": "NETFLIX.COM", "amount": 15.99},
        {"merchant": "Chipotle", "description": "CHIPOTLE 1234 SAN FRANCISCO", "amount": 12.50},
        {"merchant": "Walgreens", "description": "WALGREENS #1234", "amount": 8.75},
    ]


@pytest.fixture
def sample_portfolio() -> list[dict]:
    """Sample portfolio for analytics benchmarks."""
    return [
        {"symbol": "AAPL", "shares": 100, "cost_basis": 150.00},
        {"symbol": "GOOGL", "shares": 50, "cost_basis": 2800.00},
        {"symbol": "MSFT", "shares": 75, "cost_basis": 380.00},
        {"symbol": "AMZN", "shares": 30, "cost_basis": 3200.00},
        {"symbol": "TSLA", "shares": 40, "cost_basis": 250.00},
    ]
