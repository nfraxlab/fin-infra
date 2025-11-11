"""Tests for compliance tracking and event logging."""

import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.compliance import add_compliance_tracking, log_compliance_event


def test_add_compliance_tracking():
    """Test add_compliance_tracking enables middleware."""
    app = FastAPI()
    add_compliance_tracking(app)

    # Verify middleware is added
    assert len(app.user_middleware) > 0


def test_compliance_tracking_banking_endpoint(caplog):
    """Test compliance event logged for banking endpoint."""
    # Set log level to capture INFO logs
    caplog.set_level(logging.INFO, logger="fin_infra.compliance")

    app = FastAPI()
    add_compliance_tracking(app, track_banking=True)

    @app.get("/banking/accounts")
    async def get_accounts():
        return {"accounts": []}

    client = TestClient(app)
    response = client.get("/banking/accounts")

    assert response.status_code == 200
    # Check log contains compliance event
    assert any("banking.data_accessed" in record.message for record in caplog.records)


def test_compliance_tracking_credit_endpoint(caplog):
    """Test compliance event logged for credit endpoint."""
    caplog.set_level(logging.INFO, logger="fin_infra.compliance")

    app = FastAPI()
    add_compliance_tracking(app, track_credit=True)

    @app.get("/credit/report")
    async def get_credit_report():
        return {"score": 750}

    client = TestClient(app)
    response = client.get("/credit/report")

    assert response.status_code == 200
    assert any("credit.report_accessed" in record.message for record in caplog.records)


def test_compliance_tracking_brokerage_endpoint(caplog):
    """Test compliance event logged for brokerage endpoint."""
    caplog.set_level(logging.INFO, logger="fin_infra.compliance")

    app = FastAPI()
    add_compliance_tracking(app, track_brokerage=True)

    @app.get("/brokerage/positions")
    async def get_positions():
        return {"positions": []}

    client = TestClient(app)
    response = client.get("/brokerage/positions")

    assert response.status_code == 200
    assert any("brokerage.data_accessed" in record.message for record in caplog.records)


def test_compliance_tracking_post_request_not_logged(caplog):
    """Test POST requests are not logged as compliance events."""
    app = FastAPI()
    add_compliance_tracking(app)

    @app.post("/banking/accounts")
    async def create_account():
        return {"id": "account123"}

    client = TestClient(app)
    response = client.post("/banking/accounts")

    assert response.status_code == 200
    # No compliance event for POST
    assert not any("banking.data_accessed" in record.message for record in caplog.records)


def test_compliance_tracking_non_financial_endpoint_not_logged(caplog):
    """Test non-financial endpoints are not logged."""
    app = FastAPI()
    add_compliance_tracking(app)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    # No compliance event for /health
    assert not any("compliance_event" in record.message for record in caplog.records)


def test_compliance_tracking_error_response_not_logged(caplog):
    """Test error responses (4xx, 5xx) are not logged as compliance events."""
    app = FastAPI()
    add_compliance_tracking(app)

    @app.get("/banking/accounts")
    async def get_accounts():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    client = TestClient(app)
    response = client.get("/banking/accounts")

    assert response.status_code == 404
    # No compliance event for error response
    assert not any("banking.data_accessed" in record.message for record in caplog.records)


def test_compliance_tracking_custom_callback():
    """Test custom event callback is invoked."""
    app = FastAPI()
    events = []

    def custom_callback(event: str, context: dict):
        events.append((event, context))

    add_compliance_tracking(app, on_event=custom_callback)

    @app.get("/banking/accounts")
    async def get_accounts():
        return {"accounts": []}

    client = TestClient(app)
    response = client.get("/banking/accounts")

    assert response.status_code == 200
    assert len(events) == 1
    assert events[0][0] == "banking.data_accessed"
    assert events[0][1]["endpoint"] == "/banking/accounts"


def test_compliance_tracking_selective_tracking():
    """Test selective tracking (only banking, not credit)."""
    app = FastAPI()
    events = []

    def capture_event(event: str, context: dict):
        events.append(event)

    add_compliance_tracking(app, track_banking=True, track_credit=False, on_event=capture_event)

    @app.get("/banking/accounts")
    async def get_banking():
        return {}

    @app.get("/credit/report")
    async def get_credit():
        return {}

    client = TestClient(app)
    client.get("/banking/accounts")
    client.get("/credit/report")

    # Only banking tracked
    assert "banking.data_accessed" in events
    assert "credit.report_accessed" not in events


def test_log_compliance_event(caplog):
    """Test log_compliance_event helper."""
    caplog.set_level(logging.INFO, logger="fin_infra.compliance")

    app = FastAPI()

    log_compliance_event(app, "test.event", {"user_id": "user123", "action": "test_action"})

    # Check log contains event
    assert any("test.event" in record.message for record in caplog.records)
    # Check structured context
    compliance_record = next(r for r in caplog.records if "test.event" in r.message)
    assert hasattr(compliance_record, "compliance_event")
    assert compliance_record.compliance_event == "test.event"
    assert compliance_record.user_id == "user123"


def test_log_compliance_event_without_context(caplog):
    """Test log_compliance_event with minimal args."""
    caplog.set_level(logging.INFO, logger="fin_infra.compliance")

    app = FastAPI()

    log_compliance_event(app, "minimal.event")

    assert any("minimal.event" in record.message for record in caplog.records)
    compliance_record = next(r for r in caplog.records if "minimal.event" in r.message)
    assert hasattr(compliance_record, "timestamp")
