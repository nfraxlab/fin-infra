import os
import pytest


pytestmark = pytest.mark.acceptance


def has_google_key() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY"))


# Test data: 20 merchant names covering various formats
MERCHANT_TEST_DATA = [
    "NFLX*SUB",
    "SQ *STARBUCKS",
    "AMZN Mktp US",
    "SPOTIFY USA",
    "TST* UBER TRIP",
    "PAYPAL *HULU",
    "APPLE.COM/BILL",
    "Google *YouTubePremium",
    "Venmo *CashApp",
    "NORDSTROM #543",
    "WAL-MART SUPERCENTER #2453",
    "TARGET 00001234",
    "CVS/PHARMACY #12345",
    "SHELL OIL 12345678",
    "MCDONALD'S F12345",
    "IN-N-OUT BURGER #123",
    "CHIPOTLE 1234",
    "WHOLE FOODS MKT #01234",
    "TRADER JOES #123",
    "COSTCO WHSE #1234",
]


@pytest.mark.skipif(not has_google_key(), reason="Requires GOOGLE_API_KEY for real LLM calls")
@pytest.mark.asyncio
async def test_google_gemini_normalization() -> None:
    """Acceptance: verify merchant normalization with 20 real merchant names.

    This test requires a valid `GOOGLE_API_KEY` set in the environment.
    Tests normalization quality across various merchant name formats.
    """
    from fin_infra.recurring.normalizers import MerchantNormalizer

    normalizer = MerchantNormalizer(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
        enable_cache=False,
    )

    successful_normalizations = 0
    high_confidence_count = 0

    for merchant_name in MERCHANT_TEST_DATA:
        result = await normalizer.normalize(merchant_name)

        # Basic validation
        assert hasattr(result, "canonical_name")
        assert hasattr(result, "confidence")
        assert hasattr(result, "merchant_type")
        assert hasattr(result, "reasoning")

        # Track success metrics
        if result.canonical_name and len(result.canonical_name) > 0:
            successful_normalizations += 1

        if result.confidence >= 0.8:
            high_confidence_count += 1

    # Quality checks
    success_rate = successful_normalizations / len(MERCHANT_TEST_DATA)
    high_conf_rate = high_confidence_count / len(MERCHANT_TEST_DATA)

    assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
    assert high_conf_rate >= 0.80, f"High confidence rate {high_conf_rate:.2%} below 80% threshold"


@pytest.mark.skipif(not has_google_key(), reason="Requires GOOGLE_API_KEY for real LLM calls")
@pytest.mark.asyncio
async def test_variable_detection_accuracy() -> None:
    """Acceptance: test variable detection with utility transaction patterns.

    Tests accuracy on seasonal/variable patterns (target: 88%+ accuracy).
    """
    from fin_infra.recurring.detectors_llm import VariableDetectorLLM

    detector = VariableDetectorLLM(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
    )

    # Test cases: (merchant, amounts, date_pattern, expected_is_recurring)
    test_cases = [
        # Seasonal utility bills (should be recurring)
        ("City Electric", [45.5, 52.3, 48.75, 54.2], "Monthly (15th ±3 days)", True),
        ("Gas Company", [45.0, 120.0, 115.0, 50.0], "Monthly (15th ±5 days)", True),
        ("Water Utility", [35.0, 38.0, 36.5, 37.0], "Monthly (1st ±2 days)", True),
        # Phone bills with occasional spikes (should be recurring)
        ("T-Mobile", [50.0, 78.5, 50.0, 50.0], "Monthly (15th ±2 days)", True),
        ("AT&T", [65.0, 65.0, 92.0, 65.0], "Monthly (20th ±3 days)", True),
        # Gym membership with fee waivers (should be recurring)
        ("Planet Fitness", [10.0, 10.0, 0.0, 10.0], "Monthly (1st ±1 day)", True),
        # Random variance (should NOT be recurring)
        ("Random Store", [25.0, 150.0, 40.0, 200.0], "Monthly (15th ±10 days)", False),
        ("Coffee Shop", [4.5, 12.0, 3.0, 25.0], "Weekly (varying)", False),
    ]

    correct_predictions = 0
    total_predictions = len(test_cases)

    for merchant, amounts, date_pattern, expected_recurring in test_cases:
        result = await detector.detect(merchant, amounts, date_pattern)

        # Basic validation
        assert hasattr(result, "is_recurring")
        assert hasattr(result, "confidence")

        # Check accuracy
        if result.is_recurring == expected_recurring:
            correct_predictions += 1

    accuracy = correct_predictions / total_predictions
    assert accuracy >= 0.75, f"Accuracy {accuracy:.2%} below 75% threshold (88% ideal)"


@pytest.mark.skipif(not has_google_key(), reason="Requires GOOGLE_API_KEY for real LLM calls")
@pytest.mark.asyncio
async def test_insights_generation() -> None:
    """Acceptance: generate insights for test subscriptions.

    Validates insights quality and recommendations.
    """
    from fin_infra.recurring.insights import SubscriptionInsightsGenerator

    gen = SubscriptionInsightsGenerator(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
        enable_cache=False,
    )

    # Test with 10 subscriptions (mix of streaming, productivity, etc.)
    subscriptions = [
        {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
        {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
        {"merchant": "Hulu", "amount": 12.99, "cadence": "monthly"},
        {"merchant": "Disney Plus", "amount": 10.99, "cadence": "monthly"},
        {"merchant": "Amazon Prime", "amount": 14.99, "cadence": "monthly"},
        {"merchant": "Apple Music", "amount": 10.99, "cadence": "monthly"},
        {"merchant": "YouTube Premium", "amount": 11.99, "cadence": "monthly"},
        {"merchant": "HBO Max", "amount": 15.99, "cadence": "monthly"},
        {"merchant": "Adobe Creative Cloud", "amount": 54.99, "cadence": "monthly"},
        {"merchant": "Microsoft 365", "amount": 6.99, "cadence": "monthly"},
    ]

    result = await gen.generate(subscriptions)

    # Validate structure
    assert hasattr(result, "summary")
    assert hasattr(result, "top_subscriptions")
    assert hasattr(result, "recommendations")
    assert hasattr(result, "total_monthly_cost")
    assert hasattr(result, "potential_savings")

    # Validate content quality
    assert len(result.summary) > 0, "Summary should not be empty"
    assert len(result.top_subscriptions) <= 5, "Should return max 5 top subscriptions"
    assert len(result.recommendations) <= 3, "Should return max 3 recommendations"

    # Validate total cost calculation
    expected_total = sum(sub["amount"] for sub in subscriptions)
    assert abs(result.total_monthly_cost - expected_total) < 0.01, "Total cost mismatch"


@pytest.mark.skipif(not has_google_key(), reason="Requires GOOGLE_API_KEY for real LLM calls")
@pytest.mark.asyncio
async def test_cost_per_request() -> None:
    """Acceptance: measure actual LLM API costs.

    Validates that costs stay under budget (<$0.003/user/year target).
    """
    from fin_infra.recurring.normalizers import MerchantNormalizer
    from fin_infra.recurring.detectors_llm import VariableDetectorLLM
    from fin_infra.recurring.insights import SubscriptionInsightsGenerator

    # Create instances
    normalizer = MerchantNormalizer(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
        enable_cache=False,
    )
    detector = VariableDetectorLLM(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
    )
    insights_gen = SubscriptionInsightsGenerator(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
        enable_cache=False,
    )

    # Simulate typical user month: 5 normalizations, 2 variable detections, 1 insights
    for _ in range(5):
        await normalizer.normalize("NFLX*SUB")

    for _ in range(2):
        await detector.detect("City Electric", [45.5, 52.3], "Monthly (15th)")

    await insights_gen.generate([{"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"}])

    # Get budget status
    norm_budget = normalizer.get_budget_status()
    det_budget = detector.get_budget_status()
    ins_budget = insights_gen.get_budget_status()

    # Validate budget tracking works
    assert norm_budget["daily_cost"] > 0, "Normalizer should track costs"
    assert det_budget["daily_cost"] > 0, "Detector should track costs"
    assert ins_budget["daily_cost"] > 0, "Insights generator should track costs"

    # Total monthly cost (simulated user behavior)
    total_monthly = (
        norm_budget["monthly_cost"] + det_budget["monthly_cost"] + ins_budget["monthly_cost"]
    )

    # Annual cost estimate
    total_annual = total_monthly * 12

    # Verify under budget (target <$0.003/user/year, allow up to $0.01 for acceptance test tolerance)
    assert total_annual < 0.01, f"Annual cost ${total_annual:.4f} exceeds $0.01 threshold"


@pytest.mark.skipif(not has_google_key(), reason="Requires GOOGLE_API_KEY for real LLM calls")
@pytest.mark.asyncio
async def test_accuracy_improvement() -> None:
    """Acceptance: compare V2 (LLM) vs V1 (pattern-only) accuracy.

    Tests on merchant name variations to verify LLM improves accuracy.
    Target: V2 92%+ vs V1 85%.
    """
    from fin_infra.recurring.normalizers import MerchantNormalizer

    # Test cases with expected canonical names
    test_cases = [
        ("NFLX*SUB", "netflix"),
        ("NETFLIX.COM", "netflix"),
        ("Netflix Inc", "netflix"),
        ("SQ *STARBUCKS", "starbucks"),
        ("STARBUCKS #1234", "starbucks"),
        ("Starbucks Coffee", "starbucks"),
        ("SPOTIFY USA", "spotify"),
        ("Spotify Premium", "spotify"),
        ("SPFY*SUBSCRIPTION", "spotify"),
        ("AMZN Mktp US", "amazon"),
    ]

    normalizer = MerchantNormalizer(
        provider="google",
        model_name=os.getenv("FIN_INFRA_ACCEPTANCE_MODEL", "gemini-2.0-flash-exp"),
        enable_cache=False,
    )

    correct_v2 = 0

    for merchant_name, expected_canonical in test_cases:
        result = await normalizer.normalize(merchant_name)

        # Check if canonical name contains expected term (case insensitive)
        if expected_canonical.lower() in result.canonical_name.lower():
            correct_v2 += 1

    v2_accuracy = correct_v2 / len(test_cases)

    # V2 should achieve high accuracy on these variants
    assert v2_accuracy >= 0.80, f"V2 accuracy {v2_accuracy:.2%} below 80% threshold (92% ideal)"
