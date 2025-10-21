# Acceptance Matrix

Profiles and scenarios covered by acceptance tests.

- Default (in-memory):
  - CoinGecko ticker/ohlcv (public)
  - Alpha Vantage quote/history (key-gated, skipped if missing)
  - Demo app ping

- Redis profile:
  - Same as default plus: cache-enabled scenarios (future), with REDIS_URL=redis://localhost:6379/0
