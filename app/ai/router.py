"""
Rule-based intent router replacing OpenAI GPT-4o-mini.
"""
from dataclasses import dataclass
from app.ai.mock_ai_parser import parse_message, ParsedMessage


@dataclass
class IntentResponse:
    intent: str
    confidence: float


def classify_intent(message_text: str, current_state: str) -> IntentResponse:
    """
    Fast, free intent classification using rule-based parser.
    No API calls required.
    """
    parsed = parse_message(message_text)
    
    # If user is mid-flow and sends a location/weight, keep them in current flow
    if current_state in ["collecting_pickup", "collecting_drop", "collecting_weight", "collecting_passenger"]:
        if parsed.intent in ["unknown", "location_input"]:
            # User is likely responding to a prompt — keep in current flow
            return IntentResponse(intent="continuation", confidence=0.9)
    
    return IntentResponse(intent=parsed.intent, confidence=parsed.confidence)
