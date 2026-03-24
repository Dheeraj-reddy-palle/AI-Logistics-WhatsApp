import os

# Set required dummy env vars before Pydantic evaluates app config
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["OPENAI_API_KEY"] = "sk-mock"
os.environ["WEBHOOK_VERIFY_TOKEN"] = "mock_token"
os.environ["WHATSAPP_TOKEN"] = "mock_token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "mock_id"
os.environ["ENV"] = "dev"

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


# 2. Mock Redis (for state machine used in agent)
@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.setnx.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.expire.return_value = True
    mock.geosearch.return_value = []
    return mock


# 3. Mock DB Session
@pytest.fixture
def mock_db_session():
    return AsyncMock()
