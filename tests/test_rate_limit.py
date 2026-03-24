import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_security_middleware_skips_in_dev_mode(async_client):
    """In dev mode (ENV=dev), security middleware should pass all requests through."""

    with patch("app.ai.agent.handle_incoming_message", new_callable=AsyncMock) as mock_handler, \
         patch("app.ai.chat_formatter.format_response", new_callable=AsyncMock) as mock_format:

        mock_handler.return_value = {"reply": "OK", "state": "idle", "booking_id": None}
        mock_format.return_value = "OK"

        # No signature header — should still work in dev mode
        response = await async_client.post(
            "/api/v1/webhook",
            data={"MessageSid": "msg1", "From": "whatsapp:+911234567890", "Body": "Hi"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Test the health check endpoint returns valid status."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
