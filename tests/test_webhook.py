import pytest
from unittest.mock import patch

def get_valid_payload(msg_id="wamid.HBgL", phone="1234567890"):
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"wa_id": phone}],
                    "messages": [{"id": msg_id, "type": "text", "text": {"body": "Hi"}}]
                }
            }]
        }]
    }

@pytest.mark.asyncio
async def test_webhook_returns_200_ok(async_client, mock_redis, mock_celery_task):
    """Test valid request returns 200 without blocking routing."""
    
    # Mock signature verification
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=True):
        response = await async_client.post(
            "/api/v1/webhook", 
            json=get_valid_payload(),
            headers={"X-Hub-Signature-256": "sha256=mocked_sig"}
        )
        
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # Ensure celery task was triggered
    mock_celery_task.assert_called_once()

@pytest.mark.asyncio
async def test_webhook_invalid_payload_handling(async_client, mock_redis):
    """Test webhook handles malformed JSON without crashing."""
    
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=True):
        response = await async_client.post(
            "/api/v1/webhook", 
            json={"invalid": "payload"},
            headers={"X-Hub-Signature-256": "sha256=mocked_sig"}
        )
    
    # Should still return 200 to satisfy Meta, catching exceptions internally
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_webhook_signature_rejection(async_client):
    """Test invalid signature triggers 403."""
    with patch("app.api.middleware.security.hmac.compare_digest", return_value=False):
        response = await async_client.post(
            "/api/v1/webhook", 
            json=get_valid_payload(),
            headers={"X-Hub-Signature-256": "sha256=invalid"}
        )
        
    assert response.status_code == 403
