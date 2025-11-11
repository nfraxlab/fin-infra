from __future__ import annotations

import types
import httpx
import pytest

from fin_infra.utils.http import aget_json


class _FakeResponse:
    def __init__(self, json_data: dict):
        self._json = json_data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._json


class _FakeAsyncClient:
    instances: list["_FakeAsyncClient"] = []

    def __init__(self, *, timeout: httpx.Timeout | None = None):
        self.timeout = timeout
        self._get_impl: types.FunctionType | None = None  # type: ignore[name-defined]
        _FakeAsyncClient.instances.append(self)

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def get(self, url: str, **kwargs):  # noqa: ANN201
        if self._get_impl is None:
            raise RuntimeError("_get_impl not set")
        return await self._get_impl(url, **kwargs)  # type: ignore[misc]


@pytest.mark.asyncio
async def test_aget_json_retries_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    async def flaky_get(_url: str, **_kw):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.HTTPError("boom")
        return _FakeResponse({"ok": True})

    def fake_client_factory(*, timeout=None):  # noqa: ANN001
        c = _FakeAsyncClient(timeout=timeout)
        c._get_impl = flaky_get  # type: ignore[assignment]
        return c

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    data = await aget_json("https://example.com")
    assert data == {"ok": True}
    assert attempts["n"] == 3  # two failures, one success


@pytest.mark.asyncio
async def test_aget_json_raises_after_attempts(monkeypatch):
    async def always_fail(_url: str, **_kw):
        raise httpx.HTTPError("fail")

    def fake_client_factory(*, timeout=None):  # noqa: ANN001
        c = _FakeAsyncClient(timeout=timeout)
        c._get_impl = always_fail  # type: ignore[assignment]
        return c

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    with pytest.raises(httpx.HTTPError):
        await aget_json("https://example.com")


@pytest.mark.asyncio
async def test_aget_json_uses_default_timeout(monkeypatch):
    seen: list[httpx.Timeout] = []

    async def ok(_url: str, **_kw):
        return _FakeResponse({"ok": True})

    def fake_client_factory(*, timeout=None):  # noqa: ANN001
        # capture the Timeout object
        if isinstance(timeout, httpx.Timeout):
            seen.append(timeout)
        c = _FakeAsyncClient(timeout=timeout)
        c._get_impl = ok  # type: ignore[assignment]
        return c

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    await aget_json("https://example.com")
    assert seen, "Timeout should be provided to AsyncClient"
    t = seen[0]
    # httpx.Timeout with a single float sets all phases equally
    assert t.connect == 20.0 and t.read == 20.0 and t.write == 20.0 and t.pool == 20.0
