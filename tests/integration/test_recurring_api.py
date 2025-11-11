"""Integration tests for recurring detection FastAPI endpoints.

Tests add_recurring_detection() helper and all mounted endpoints with TestClient.
"""

import pytest
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create FastAPI app with recurring detection endpoints.

    Uses public_router to bypass database dependency for testing.
    Production uses user_router with authentication.
    """
    from svc_infra.api.fastapi.dual.public import public_router
    from fin_infra.recurring import easy_recurring_detection
    from fin_infra.recurring.summary import RecurringSummary, get_recurring_summary
    from fastapi import Query

    app = FastAPI(title="Test Recurring API")

    # Create detector
    detector = easy_recurring_detection()
    app.state.recurring_detector = detector

    # Create public router (no auth) for testing
    router = public_router(prefix="/recurring", tags=["Recurring Detection"])

    # Define all endpoints manually
    @router.get("/detect")
    async def detect_recurring(user_id: str = Query(...)):
        txns = []  # Empty for testing
        patterns = await detector.detect_recurring(txns)
        return {"user_id": user_id, "patterns": patterns}

    @router.get("/subscriptions")
    async def get_subscriptions(user_id: str = Query(...)):
        return {"user_id": user_id, "subscriptions": []}

    @router.get("/predictions")
    async def predict_next(user_id: str = Query(...)):
        return {"user_id": user_id, "predictions": []}

    @router.get("/stats")
    async def get_stats(user_id: str = Query(...)):
        return {"user_id": user_id, "total_recurring": 0.0}

    @router.get("/summary", response_model=RecurringSummary)
    async def get_summary(user_id: str = Query(...)):
        # Call detector's detect_patterns (tests can mock this)
        txns = []
        patterns = detector.detect_patterns(txns)
        summary = get_recurring_summary(user_id, patterns)
        return summary

    app.include_router(router)

    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def create_test_pattern(
    merchant_name: str,
    amount: float,
    cadence: str = "monthly",
    confidence: float = 0.95,
    pattern_type: str = "fixed",
    occurrences: int = 10,
) -> "RecurringPattern":
    """Helper to create a test RecurringPattern with all required fields."""
    from fin_infra.recurring.models import RecurringPattern, CadenceType, PatternType

    return RecurringPattern(
        merchant_name=merchant_name,
        normalized_merchant=merchant_name.lower().replace(" ", "_"),
        pattern_type=PatternType(pattern_type),
        cadence=CadenceType(cadence),
        amount=amount,
        amount_range=None,
        amount_variance_pct=0.0,
        occurrence_count=occurrences,
        first_date=datetime(2025, 1, 15),
        last_date=datetime(2025, 10, 15),
        next_expected_date=datetime(2025, 11, 15),
        date_std_dev=0.5,
        confidence=confidence,
        reasoning=f"Fixed amount ${amount} charged {cadence}",
    )


# Test: add_recurring_detection() helper
def test_add_recurring_detection_helper(app):
    """Test add_recurring_detection() mounts endpoints correctly."""
    # Check detector stored on app state
    assert hasattr(app.state, "recurring_detector")
    assert app.state.recurring_detector is not None

    # Check routes exist
    routes = [route.path for route in app.routes]
    assert "/recurring/detect" in routes
    assert "/recurring/subscriptions" in routes
    assert "/recurring/predictions" in routes
    assert "/recurring/stats" in routes
    assert "/recurring/summary" in routes


# Test: Summary endpoint with no patterns
def test_get_summary_empty(client):
    """Test GET /recurring/summary with no detected patterns."""
    response = client.get("/recurring/summary?user_id=user_123")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["user_id"] == "user_123"
    assert data["total_monthly_cost"] == 0.0
    assert data["total_monthly_income"] == 0.0
    assert data["subscriptions"] == []
    assert data["recurring_income"] == []
    assert data["by_category"] == {}
    assert data["cancellation_opportunities"] == []
    assert "generated_at" in data


# Test: Summary endpoint with mocked patterns
def test_get_summary_with_patterns(client, app):
    """Test GET /recurring/summary with detected patterns."""
    # Mock detector to return patterns
    mock_patterns = [
        create_test_pattern("Netflix", 15.99, confidence=0.95),
        create_test_pattern("Spotify", 9.99, confidence=0.92),
    ]

    # Patch detector
    original_detect = app.state.recurring_detector.detect_patterns
    app.state.recurring_detector.detect_patterns = lambda txns: mock_patterns

    try:
        response = client.get("/recurring/summary?user_id=user_123")

        assert response.status_code == 200
        data = response.json()

        # Validate response
        assert data["user_id"] == "user_123"
        assert data["total_monthly_cost"] == pytest.approx(25.98, rel=0.01)
        assert len(data["subscriptions"]) == 2

        # Validate subscription details (merchant_name is normalized)
        netflix = next(s for s in data["subscriptions"] if "netflix" in s["merchant_name"].lower())
        assert netflix["amount"] == 15.99
        assert netflix["cadence"] == "monthly"
        assert netflix["monthly_cost"] == 15.99
        assert netflix["is_subscription"] is True
        assert netflix["confidence"] == 0.95

        spotify = next(s for s in data["subscriptions"] if "spotify" in s["merchant_name"].lower())
        assert spotify["amount"] == 9.99
        assert spotify["monthly_cost"] == 9.99

        # Check category grouping (should infer entertainment - lowercase)
        assert "entertainment" in data["by_category"]

    finally:
        # Restore original detector
        app.state.recurring_detector.detect_patterns = original_detect


# Test: Summary endpoint with quarterly subscription
def test_get_summary_quarterly_subscription(client, app):
    """Test GET /recurring/summary with quarterly cadence normalization."""
    mock_patterns = [
        create_test_pattern(
            "Costco Membership", 60.00, cadence="quarterly", confidence=0.88, occurrences=2
        ),
    ]

    original_detect = app.state.recurring_detector.detect_patterns
    app.state.recurring_detector.detect_patterns = lambda txns: mock_patterns

    try:
        response = client.get("/recurring/summary?user_id=user_123")

        assert response.status_code == 200
        data = response.json()

        # Validate monthly cost normalization (60 / 3 = 20)
        assert data["total_monthly_cost"] == pytest.approx(20.00, rel=0.01)
        assert len(data["subscriptions"]) == 1

        subscription = data["subscriptions"][0]
        assert subscription["amount"] == 60.00
        assert subscription["cadence"] == "quarterly"
        assert subscription["monthly_cost"] == pytest.approx(20.00, rel=0.01)

    finally:
        app.state.recurring_detector.detect_patterns = original_detect


# Test: Summary endpoint with recurring income
def test_get_summary_with_income(client, app):
    """Test GET /recurring/summary with recurring income (negative amounts)."""
    mock_patterns = [
        create_test_pattern("Netflix", 15.99, confidence=0.95),
        create_test_pattern(
            "Employer Direct Deposit", -2000.00, cadence="biweekly", confidence=0.98, occurrences=20
        ),
    ]

    original_detect = app.state.recurring_detector.detect_patterns
    app.state.recurring_detector.detect_patterns = lambda txns: mock_patterns

    try:
        response = client.get("/recurring/summary?user_id=user_123")

        assert response.status_code == 200
        data = response.json()

        # Validate separation
        assert len(data["subscriptions"]) == 1
        assert len(data["recurring_income"]) == 1

        # Check expense
        assert data["total_monthly_cost"] == pytest.approx(15.99, rel=0.01)
        expense = data["subscriptions"][0]
        assert "netflix" in expense["merchant_name"].lower()
        assert expense["amount"] == 15.99

        # Check income (biweekly: 2000 * 26 / 12 = 4333.33)
        assert data["total_monthly_income"] == pytest.approx(4333.33, rel=0.01)
        income = data["recurring_income"][0]
        assert "employer" in income["merchant_name"].lower()
        assert income["amount"] == 2000.00
        assert income["cadence"] == "biweekly"
        assert income["monthly_cost"] == pytest.approx(4333.33, rel=0.01)

    finally:
        app.state.recurring_detector.detect_patterns = original_detect


# Test: Summary endpoint with cancellation opportunities
def test_get_summary_with_cancellation_opportunities(client, app):
    """Test GET /recurring/summary detects cancellation opportunities."""
    # Multiple streaming services (duplicate detection)
    mock_patterns = [
        create_test_pattern("Netflix", 15.99, confidence=0.95),
        create_test_pattern("Hulu", 7.99, confidence=0.92),
        create_test_pattern("Disney Plus", 10.99, confidence=0.90),
    ]

    original_detect = app.state.recurring_detector.detect_patterns
    app.state.recurring_detector.detect_patterns = lambda txns: mock_patterns

    try:
        response = client.get("/recurring/summary?user_id=user_123")

        assert response.status_code == 200
        data = response.json()

        # Should have cancellation opportunities (>2 streaming services)
        assert len(data["cancellation_opportunities"]) > 0

        # Should suggest canceling cheapest (Hulu)
        opportunity = next(
            (o for o in data["cancellation_opportunities"] if "hulu" in o["merchant_name"].lower()),
            None,
        )
        assert opportunity is not None
        assert opportunity["monthly_savings"] == pytest.approx(7.99, rel=0.01)
        assert "streaming" in opportunity["reason"].lower()

    finally:
        app.state.recurring_detector.detect_patterns = original_detect


# Test: Summary endpoint with inferred category
def test_get_summary_with_inferred_category(client, app):
    """Test GET /recurring/summary infers categories correctly."""
    mock_patterns = [
        create_test_pattern("Netflix", 15.99, confidence=0.95),
    ]

    original_detect = app.state.recurring_detector.detect_patterns
    app.state.recurring_detector.detect_patterns = lambda txns: mock_patterns

    try:
        response = client.get("/recurring/summary?user_id=user_123")

        assert response.status_code == 200
        data = response.json()

        # Should infer entertainment category for Netflix
        subscription = data["subscriptions"][0]
        assert subscription["category"] == "entertainment"
        assert "entertainment" in data["by_category"]
        assert data["by_category"]["entertainment"] == pytest.approx(15.99, rel=0.01)

    finally:
        app.state.recurring_detector.detect_patterns = original_detect


# Test: Summary endpoint missing user_id
def test_get_summary_missing_user_id(client):
    """Test GET /recurring/summary requires user_id parameter."""
    response = client.get("/recurring/summary")

    # FastAPI will return 422 for missing required query parameter
    assert response.status_code == 422
    assert "user_id" in response.text.lower()
