import logging
import asyncio
import httpx
from app.config.settings import settings

logger = logging.getLogger(__name__)

FALLBACK_TEMPLATES = {
    "idle": "👋 Welcome to Logistics AI! I can help you book a delivery or track a shipment.",
    "collecting_pickup": "Where should we pick it up from? 📍",
    "collecting_drop": "Where do you want it delivered? 📍",
    "collecting_weight": "How much weight are you sending? 📦",
    "collecting_passenger": "Please share the passenger's phone number 📱",
    "booking_confirmed": "Got everything 👍 Should I go ahead and confirm this booking?",
    "driver_assigned": "Your driver is on the way 🚚",
    "tracking": "Here is your tracking link: ",
    "error": "Hmm, I didn’t quite get that. Can you try again?",
    "duplicate": "Message already processed.",
}

SYSTEM_PROMPT = """
You are a human-like logistics assistant on WhatsApp. 
Rewrite the given intent and data into a natural, short message. 
Do not change meaning. Do not add new info. Maximum 1-2 short lines.
Keep it conversational and friendly. You may use a relevant emoji like 👍 📍 🚚 📦.
Do NOT output JSON or explanations. Only output the final WhatsApp message string.
"""

async def format_response(intent: str, data: dict) -> str:
    """
    Takes the structured intent (state) and raw output data from the deterministic backend,
    and returns a fluid, human-like rewrite holding identical factual integrity.
    """
    raw_text = data.get("raw_reply", "")
    provider = getattr(settings, "AI_PROVIDER", "disabled").lower()
    
    if provider == "disabled":
        return raw_text
        
    # Simulate human typing delay (Optional/Configuration matched)
    if getattr(settings, "SIMULATE_DELAY", False):
        await asyncio.sleep(0.5)
    
    user_prompt = f"Intent: {intent}\nOriginal Data: {raw_text}\n\nRewrite this as a friendly WhatsApp message:"
    
    try:
        if provider == "ollama":
            message = await _call_ollama(user_prompt)
        elif provider == "huggingface":
            message = await _call_huggingface(user_prompt)
        else:
            message = raw_text
            
        if not message or len(message.strip()) == 0:
            raise ValueError("Empty AI response")
            
        logger.info(f"✨ [AI REWRITE] {intent} | Raw: {raw_text[:30]}... -> AI: {message}")
        return message.strip(' "\'')
        
    except Exception as e:
        logger.error(f"⚠️ [AI FALLBACK] Failed to format response via {provider}: {e}")
        # Fallback to predefined templates or safe raw text retaining state compatibility
        return FALLBACK_TEMPLATES.get(intent, raw_text)

async def _call_ollama(prompt: str) -> str:
    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_MODEL", "llama3")
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json().get("response", "") or ""

async def _call_huggingface(prompt: str) -> str:
    api_key = getattr(settings, "HUGGINGFACE_API_KEY", "")
    model = getattr(settings, "HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    
    if not api_key:
        raise ValueError("HUGGINGFACE_API_KEY is not set")
        
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "inputs": f"<s>[INST] {SYSTEM_PROMPT}\n\n{prompt} [/INST]",
        "parameters": {"max_new_tokens": 150, "return_full_text": False, "temperature": 0.7}
    }
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").strip() or ""
        return ""
