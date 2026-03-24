import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_idempotency_duplicate_rejection():
    """Test that duplicate msg_ids are rejected by the state machine's idempotency check."""

    with patch("app.ai.agent.state_manager") as mock_sm:
        mock_sm.check_idempotency = AsyncMock(return_value=False)

        from app.ai.agent import handle_incoming_message

        result = await handle_incoming_message("1234567890", "Book a cab", "msg_123")

    assert result["state"] == "duplicate"
    assert "already processed" in result["reply"].lower()


@pytest.mark.asyncio
async def test_idempotency_allows_new_message():
    """Test that new message IDs pass the idempotency check and proceed."""

    with patch("app.ai.agent.state_manager") as mock_sm:
        mock_sm.check_idempotency = AsyncMock(return_value=True)
        mock_sm.is_cancel_command = lambda text: False
        mock_sm.get_state = AsyncMock(return_value={"current_flow": "idle", "context": {}})

        # Patch the location resolver and parse_message to avoid side effects
        with patch("app.ai.agent.parse_message") as mock_parse:
            mock_parse.return_value = type("Parsed", (), {
                "intent": "greeting", "pickup": None, "drop": None,
                "weight": None, "service_type": "delivery", "is_remote": False,
                "confidence": 1.0,
            })()

            from app.ai.agent import handle_incoming_message
            result = await handle_incoming_message("1234567890", "Hello", "msg_new_456")

    assert result["state"] != "duplicate"
