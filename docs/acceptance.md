# Acceptance Harness (fin-infra)

This document defines the acceptance environment contract and how to run the suite locally and in CI.

## Environment contract
- Base URL: N/A (library). A minimal demo app is provided under tests/acceptance for ping checks.
- Ports: N/A (unless running profiles that expose services, e.g., Redis 6379).
- Required environment variables:
  - ALPHAVANTAGE_API_KEY: Only needed for Alpha Vantage acceptance tests. If missing, those tests are skipped.
  - REDIS_URL: Optional; when COMPOSE_PROFILES=redis is enabled, defaults to redis://localhost:6379/0.
- Seed keys: None required. Providers use sandbox/public endpoints by default; set env keys to enable more tests.

## Profiles
- In-memory (default): No external services; acceptance tests that don’t need keys will run.
- Redis (optional): Enable with `COMPOSE_PROFILES=redis` to run a local Redis for caching scenarios.

## Running locally
- In-memory only:
  - make accept
- With Redis profile:
  - COMPOSE_PROFILES=redis make accept

## CI
The acceptance workflow `.github/workflows/acceptance.yml` runs the acceptance marker. Configure repository secrets for provider keys as needed (e.g., ALPHAVANTAGE_API_KEY).

## Matrix
See `docs/acceptance-matrix.md` for the current combinations exercised.
