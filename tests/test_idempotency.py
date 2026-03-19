import pytest
from unittest.mock import patch
from tests.test_webhook import get_valid_payload

@pytest.mark.asyncio
async def test_idempotency_duplicate_rejection(async_client, mock_redis, mock_celery_task):
    """Test that duplicate msg_ids are intercepted by Redis setnx."""
    
    # Simulate Redis setnx returning False (key already exists)
    mock_redis.setnx.return_value = False
    
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=True):
        response = await async_client.post(
            "/api/v1/webhook",
            json=get_valid_payload("msg_123"),
            headers={"X-Hub-Signature-256": "sha256=mocked_sig"}
        )
        
    assert response.status_code == 200
    assert response.json().get("ack") == "duplicate"
    
    # Celery should NOT have been called for dupes
    mock_celery_task.assert_not_called()

@pytest.mark.asyncio
async def test_idempotency_ttl_set(async_client, mock_redis, mock_celery_task):
    """Ensure the idempotency key TTL is set to 24 hours."""
    
    mock_redis.setnx.return_value = True
    
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=True):
        await async_client.post(
            "/api/v1/webhook",
            json=get_valid_payload("msg_456"),
            headers={"X-Hub-Signature-256": "sha256=mocked_sig"}
        )
        
    # Check that redis.expire was called with 86400 seconds (24h)
    mock_redis.expire.assert_called_with("msg:seen:msg_456", 86400)
    mock_celery_task.assert_called_once()
