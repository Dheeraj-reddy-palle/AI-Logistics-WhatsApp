import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_agent_handles_exception_gracefully():
    """Tests that an exception during message processing returns a fallback reply
    instead of crashing the system."""

    with patch("app.ai.agent.state_manager") as mock_sm:
        mock_sm.check_idempotency = AsyncMock(return_value=True)
        mock_sm.is_cancel_command = MagicMock(return_value=False)
        mock_sm.get_state = AsyncMock(side_effect=Exception("Redis connection refused"))

        from app.ai.agent import handle_incoming_message

        result = await handle_incoming_message("1234567890", "I need a cab", "msg_test_ai")

        assert result["state"] == "error"
        assert "try again" in result["reply"].lower()
        assert result["booking_id"] is None


@pytest.mark.asyncio
async def test_duplicate_message_rejected():
    """Tests that duplicate message IDs are rejected by the idempotency check."""

    with patch("app.ai.agent.state_manager") as mock_sm:
        mock_sm.check_idempotency = AsyncMock(return_value=False)

        from app.ai.agent import handle_incoming_message

        result = await handle_incoming_message("1234567890", "Hello", "msg_duplicate")

        assert result["state"] == "duplicate"
        assert "already processed" in result["reply"].lower()


@pytest.mark.asyncio
async def test_cancel_command_resets_state():
    """Tests that cancel keywords reset user state to idle."""

    with patch("app.ai.agent.state_manager") as mock_sm:
        mock_sm.check_idempotency = AsyncMock(return_value=True)
        mock_sm.is_cancel_command = MagicMock(return_value=True)
        mock_sm.clear_state = AsyncMock()

        from app.ai.agent import handle_incoming_message

        result = await handle_incoming_message("1234567890", "cancel", "msg_cancel")

        assert result["state"] == "idle"
        mock_sm.clear_state.assert_called_once_with("1234567890")
