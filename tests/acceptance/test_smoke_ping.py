import pytest


pytestmark = [pytest.mark.acceptance]


def test_smoke_ping():
    try:
        from fastapi.testclient import TestClient  # type: ignore
        from .app import make_app  # type: ignore
    except Exception as e:  # ImportError or others
        pytest.skip(f"acceptance demo app deps missing: {e}")
    app = make_app()
    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
    assert r.json() == {"pong": "ok"}
