# AI WhatsApp Logistics Test Suite

This directory contains the production pytest suite for validating the core infrastructure, idempotency guarantees, API circuit breakers, and database race condition handling.

## 1. Setup

These tests are fully decoupled from real external services to allow for blazing fast CI/CD execution. 
- **PostgreSQL / PostGIS** is completely mocked out via `unittest.mock.AsyncMock`. No real database is required.
- **Redis** is natively intercepted and mocked to simulate various states (rate limit throttles, duplicate webhooks, GEO cache).
- **OpenAI & WhatsApp API** network transmissions are mocked perfectly.
- **Celery Tasks** `delay()` invocations are asserted rather than executed inline.

### Install Dependencies
Ensure you have the testing framework components locally installed:
```bash
pip install pytest pytest-asyncio httpx pytest-mock
```

## 2. Running the Tests

To run the complete suite with output formatting:
```bash
pytest tests/ -v
```

## 3. Test Coverage Highlights

- `test_webhook.py`: Validates FastAPI parsing and HMAC signature rejection (Requires 403 response).
- `test_idempotency.py`: Proves `app.api.routes.webhook` strictly drops duplicates within the 24-hour Meta retry window and refuses to enqueue extra tasks.
- `test_rate_limit.py`: Shows that overlapping sliding windows accurately sum metrics via Redis Pipelines and throw `429 Too Many Requests`.
- `test_driver_service.py`: Simulates Geolocation lookups via Mocked `redis.geosearch` and proves DB table locking (`with_for_update`) prevents double-assignment race conditions.
- `test_ai_fallback.py`: Forces `openai.APITimeoutError` exceptions to prove the 2-try timeout rule guarantees users receive a strict text-fallback rather than infinite system starvation.
