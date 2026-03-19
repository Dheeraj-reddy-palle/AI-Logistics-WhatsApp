import pytest
from unittest.mock import patch
from tests.test_webhook import get_valid_payload

@pytest.mark.asyncio
async def test_rate_limit_throttle_rejection(async_client, mock_redis, mock_celery_task):
    """Ensure heavy bursts from single Phone/IPs return 429 globally."""
    
    # 60 requests in the sliding window violates the limit of 50.
    pipe_mock = mock_redis.pipeline.return_value
    pipe_mock.execute.return_value = [1, 1, 60] 
    
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=True):
        response = await async_client.post(
            "/api/v1/webhook",
            json=get_valid_payload(),
            headers={"X-Hub-Signature-256": "sha256=mocked_sig"}
        )
    
    # Security Middleware aborts execution and throws 429 Too Many Requests
    assert response.status_code == 429
    assert response.json().get("detail") == "Sender Rate Limited"
    mock_celery_task.assert_not_called()
