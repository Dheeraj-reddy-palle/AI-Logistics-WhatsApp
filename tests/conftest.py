import os

# Set required dummy env vars before Pydantic evaluates app config
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["OPENAI_API_KEY"] = "sk-mock"
os.environ["WEBHOOK_VERIFY_TOKEN"] = "mock_token"
os.environ["WHATSAPP_TOKEN"] = "mock_token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "mock_id"

import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock

# Import the FastAPI app
from app.main import app

# Configuration
@pytest.fixture
def anyio_backend():
    return "asyncio"

# 1. Async HTTP Client
@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client

# 2. Mock Redis
# We use AsyncMock directly to easily mock setnx, pipeline, etc., 
# avoiding fakeredis quirks with advanced zsets if not needed.
@pytest.fixture
def mock_redis(mocker):
    mock = AsyncMock()
    # Mock setnx for idempotency
    mock.setnx.return_value = True
    
    # Mock pipeline for rate limiter (must be MagicMock because pipeline is sync creation)
    pipe_mock = MagicMock()
    
    # We mock pipeline.execute() to be an asyncio coroutine returning a list!
    async_exec = AsyncMock(return_value=[1, 1, 10])
    pipe_mock.execute = async_exec
    
    mock.pipeline.return_value = pipe_mock
    
    # Mock geosearch for drivers
    mock.geosearch.return_value = []
    
    mocker.patch("redis.asyncio.from_url", return_value=mock)
    mocker.patch("app.db.session.redis_client", mock)
    
    # Also patch across the module space
    mocker.patch("app.api.middleware.security.SecurityMiddleware.redis_client", mock, create=True)
    mocker.patch("app.services.driver_service.redis_client", mock, create=True)
    return mock

# 3. Mock DB Session
@pytest.fixture
def mock_db_session():
    return AsyncMock()

# 4. Mock Celery Task
@pytest.fixture
def mock_celery_task(mocker):
    return mocker.patch("app.api.routes.webhook.process_whatsapp_ai_request.delay")
