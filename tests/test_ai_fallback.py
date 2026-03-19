import pytest
import openai
from unittest.mock import AsyncMock, patch
from collections import namedtuple
from app.ai.agent import handle_incoming_message

IntentResponse = namedtuple("IntentResponse", ["intent", "confidence"])

@pytest.mark.asyncio
@patch("app.ai.agent.client.chat.completions.create", new_callable=AsyncMock)
@patch("app.ai.agent.classify_intent", new_callable=AsyncMock)
@patch("app.ai.agent.state_manager.get_state", new_callable=AsyncMock)
@patch("app.ai.agent.state_manager.check_idempotency", new_callable=AsyncMock)
async def test_openai_timeout_triggers_fallback(mock_idem, mock_get_state, mock_classify, mock_openai, mock_redis):
    """Tests that a 503/Timeout from OpenAI does NOT crash the worker 
    and handles retries/fallback gracefully."""
    
    mock_idem.return_value = True
    mock_get_state.return_value = {"current_flow": "idle", "context": {}}
    mock_classify.return_value = IntentResponse(intent="booking", confidence=1.0)
    
    # Force OpenAI to consistently fail via Side Effect
    mock_openai.side_effect = openai.APITimeoutError("Request timed out from tests")
    
    with patch("app.ai.agent.WhatsAppClient", autospec=True) as mock_wa_class:
        mock_wa_instance = mock_wa_class.return_value
        mock_wa_instance.send_text = AsyncMock()
        
        await handle_incoming_message("1234567890", "I need 2 tons moved", "msg_test_ai")
        
        # Verify OpenAI attempted 2 iterations logic as written in patch
        assert mock_openai.call_count == 2
        
        # Verify fallback string was triggered and sent back automatically!
        mock_wa_instance.send_text.assert_called_with(
            "1234567890", 
            "Our AI booking assistant is currently facing high volume. Please send your pickup and dropoff locations strictly to continue!"
        )
