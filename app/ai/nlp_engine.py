"""
Mock AI Parser - Rule-based NLP replacement for OpenAI.
Uses regex and keyword matching to extract:
- intent (booking, tracking, greeting, confirmation, cancel, driver_update, unknown)
- service_type (cab or cargo)
- pickup location
- drop location
- weight (kg) — cargo only
- remote booking flag
- passenger phone
- coordinates / map links
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedMessage:
    """Result of parsing a user message"""
    intent: str = "unknown"
    confidence: float = 0.0
    pickup: Optional[str] = None
    drop: Optional[str] = None
    weight: Optional[float] = None
    is_remote: bool = False
    passenger_phone: Optional[str] = None
    service_type: str = "cargo"  # 'cab' or 'cargo'
    raw_text: str = ""


# Intent keywords
BOOKING_KEYWORDS = [
    "book", "send", "deliver", "pickup", "pick up", "transport",
    "ship", "move", "truck", "van", "car", "from", "to", "shipment",
    "dispatch", "courier", "load", "cargo", "freight",
    "cab", "ride", "taxi", "auto", "ola", "uber", "drop me",
    "take me", "go to", "need a ride", "need ride", "book cab",
    "book ride", "book auto", "bike", "moto",
]

CAB_KEYWORDS = [
    "cab", "ride", "taxi", "auto", "ola", "uber", "drop me",
    "take me", "go to", "need a ride", "need ride", "book cab",
    "book ride", "book auto", "bike", "moto", "rickshaw",
    "rapido", "indriver",
]

TRACKING_KEYWORDS = [
    "track", "where", "status", "location", "eta", "update",
    "how far", "when will", "arrived",
]

GREETING_KEYWORDS = [
    "hi", "hello", "hey", "good morning", "good evening",
    "good afternoon", "hola", "namaste", "start",
]

CONFIRMATION_KEYWORDS = [
    "yes", "confirm", "ok", "okay", "sure", "proceed", 
    "go ahead", "accept", "agreed", "done", "yep", "yeah",
]

CANCEL_KEYWORDS = [
    "cancel", "start over", "reset", "restart", "stop", "quit", "no",
]

REMOTE_BOOKING_PHRASES = [
    "for my friend", "for my brother", "for my sister",
    "for my mother", "for my father", "for my family",
    "for someone", "send for someone", "book for someone",
    "for another person", "for my colleague", "on behalf",
    "for my wife", "for my husband", "for my boss",
]

# Patterns
WEIGHT_PATTERN = re.compile(r'(-?\d+(?:\.\d+)?)\s*(?:kg|kgs|kilogram|kilograms|kilo)', re.IGNORECASE)
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\d{10}')
FROM_TO_PATTERN = re.compile(r'from\s+(.+?)\s+to\s+(.+?)(?:\s+\d+(?:\.\d+)?\s*(?:kg|kgs)|\s*$)', re.IGNORECASE)
SIMPLE_TO_PATTERN = re.compile(r'^(.+?)\s+to\s+(.+?)$', re.IGNORECASE)
COORD_PATTERN = re.compile(r'(-?\d{1,3}\.\d{2,8})\s*[,\s]\s*(-?\d{1,3}\.\d{2,8})')


def parse_message(text: str) -> ParsedMessage:
    """
    Parse a user message to extract intent, locations, weight, and booking info.
    """
    result = ParsedMessage(raw_text=text)
    text_lower = text.strip().lower()
    
    # 0. Detect service type (cab vs cargo)
    for kw in CAB_KEYWORDS:
        if kw in text_lower:
            result.service_type = "cab"
            break
    
    # 1. Detect remote booking
    for phrase in REMOTE_BOOKING_PHRASES:
        if phrase in text_lower:
            result.is_remote = True
            result.intent = "booking"
            result.confidence = 0.9
            break
    
    # 2. Extract weight
    weight_match = WEIGHT_PATTERN.search(text)
    if weight_match:
        result.weight = float(weight_match.group(1))
    
    # 3. Extract phone numbers (for passenger)
    phones = PHONE_PATTERN.findall(text)
    if phones:
        # The last phone number is likely the passenger's
        result.passenger_phone = phones[-1].strip()
    
    # 4. Extract pickup/drop from "from X to Y" pattern
    from_to_match = FROM_TO_PATTERN.search(text)
    if from_to_match:
        result.pickup = from_to_match.group(1).strip()
        result.drop = from_to_match.group(2).strip()
        result.intent = "booking"
        result.confidence = 0.95
    else:
        # Try simple "X to Y" pattern
        # Remove weight from text first for cleaner parsing
        clean_text = WEIGHT_PATTERN.sub('', text).strip()
        clean_text = re.sub(r'\b(send|book|deliver|truck|van|car)\b', '', clean_text, flags=re.IGNORECASE).strip()
        
        simple_match = SIMPLE_TO_PATTERN.search(clean_text)
        if simple_match:
            result.pickup = simple_match.group(1).strip()
            result.drop = simple_match.group(2).strip()
            result.intent = "booking"
            result.confidence = 0.90
    
    # 5. Classify intent if not already set
    if result.intent == "unknown":
        result.intent, result.confidence = _classify_intent(text_lower)
    
    return result


def _classify_intent(text: str) -> tuple:
    """Classify intent using keyword matching. Returns (intent, confidence)."""
    
    # Check cancel first (highest priority)
    for kw in CANCEL_KEYWORDS:
        if kw in text:
            return ("cancel", 0.95)
    
    # Check confirmations 
    for kw in CONFIRMATION_KEYWORDS:
        if text.strip() == kw or text.strip().startswith(kw):
            return ("confirmation", 0.95)
    
    # Check greetings
    words = text.split()
    for kw in GREETING_KEYWORDS:
        if kw in words or text.startswith(kw):
            return ("greeting", 0.90)
    
    # Check tracking
    for kw in TRACKING_KEYWORDS:
        if kw in text:
            return ("tracking", 0.85)
    
    # Check booking
    for kw in BOOKING_KEYWORDS:
        if kw in text:
            return ("booking", 0.80)
    
    # If there's a coordinate pattern or map link, likely a location input  
    if COORD_PATTERN.search(text) or "maps.app.goo.gl" in text or "goo.gl/maps" in text or "maps.google.com" in text:
        return ("location_input", 0.85)
    
    # Default
    return ("unknown", 0.3)
