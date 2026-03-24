import pytest
from unittest.mock import patch, AsyncMock


def get_twilio_form_data(msg_id="wamid.HBgL", phone="whatsapp:+911234567890", text="Hi"):
    """Simulates Twilio sandbox form-encoded payload"""
    return {
        "MessageSid": msg_id,
        "From": phone,
        "Body": text,
    }


@pytest.mark.asyncio
async def test_webhook_returns_twiml_response(async_client):
    """Test valid Twilio request returns TwiML XML response."""

    with patch("app.ai.agent.handle_incoming_message", new_callable=AsyncMock) as mock_handler, \
         patch("app.ai.chat_formatter.format_response", new_callable=AsyncMock) as mock_format:

        mock_handler.return_value = {"reply": "Hello!", "state": "idle", "booking_id": None}
        mock_format.return_value = "Hello!"

        response = await async_client.post(
            "/api/v1/webhook",
            data=get_twilio_form_data(),
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Message>" in response.text
    assert "Hello!" in response.text


@pytest.mark.asyncio
async def test_webhook_handles_error_gracefully(async_client):
    """Test webhook returns fallback message when handler throws an exception."""

    with patch("app.ai.agent.handle_incoming_message", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = Exception("Test failure")

        response = await async_client.post(
            "/api/v1/webhook",
            data=get_twilio_form_data(),
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

    assert response.status_code == 200
    assert "something went wrong" in response.text


@pytest.mark.asyncio
async def test_webhook_unsupported_content_type(async_client):
    """Test webhook rejects unsupported content types."""

    response = await async_client.post(
        "/api/v1/webhook",
        json={"invalid": "payload"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"


@pytest.mark.asyncio
async def test_webhook_location_pin(async_client):
    """Test that Twilio location pins (Latitude/Longitude) are parsed correctly."""

    with patch("app.ai.agent.handle_incoming_message", new_callable=AsyncMock) as mock_handler, \
         patch("app.ai.chat_formatter.format_response", new_callable=AsyncMock) as mock_format:

        mock_handler.return_value = {"reply": "Got location", "state": "idle", "booking_id": None}
        mock_format.return_value = "Got location"

        response = await async_client.post(
            "/api/v1/webhook",
            data={
                "MessageSid": "msg_loc",
                "From": "whatsapp:+911234567890",
                "Body": "",
                "Latitude": "17.385",
                "Longitude": "78.486",
            },
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

    assert response.status_code == 200
    # Verify the handler was called with lat,lng as the message text
    call_args = mock_handler.call_args
    assert "17.385,78.486" in call_args[0][1]
