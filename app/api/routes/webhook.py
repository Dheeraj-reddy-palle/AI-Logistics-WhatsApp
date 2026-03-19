"""
Webhook endpoints for WhatsApp message ingestion.
Supports both:
1. Simplified local testing format: {"message_id", "phone", "text"}
2. Meta WhatsApp Cloud API format (original)
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import logging

from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class SimpleWebhookPayload(BaseModel):
    """Simplified payload for local testing (Scenario 10: Mock WhatsApp)"""
    message_id: str
    phone: str
    text: str


@router.post("/webhook")
async def receive_message(request: Request):
    """
    Main webhook endpoint.
    Auto-detects payload format:
    - Twilio Sandbox: application/x-www-form-urlencoded → returns TwiML XML
    - Simple: {"message_id", "phone", "text"}
    - Meta: {"entry": [{"changes": [...]}]}
    """
    content_type = request.headers.get("content-type", "")
    
    # 1. Twilio Sandbox Format (form-encoded)
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        message_text = form.get("Body", "")
        
        # Native WhatsApp location pin support
        latitude = form.get("Latitude")
        longitude = form.get("Longitude")
        if latitude and longitude:
            message_text = f"{latitude},{longitude}"
            
        phone = form.get("From", "")  # e.g. "whatsapp:+919951049235"
        phone_clean = phone.replace("whatsapp:", "")  # strip prefix for state machine
        message_id = form.get("MessageSid", "")
        
        logger.info(f"[WEBHOOK] Twilio payload: phone={phone_clean} msg_id={message_id} text={message_text[:80]}")
        
        from app.ai.agent import handle_incoming_message
        from app.ai.chat_formatter import format_response
        
        try:
            # Pass to system logic
            result = await handle_incoming_message(phone_clean, message_text, message_id)
            
            # Conversational formatting
            formatted_reply = await format_response(result["state"], {"raw_reply": result["reply"]})
            
            logger.info(f">>> [TWILIO REPLY TO {phone}]: {formatted_reply[:100]}")
        except Exception as e:
            logger.error(f"Error processing Twilio message: {e}", exc_info=True)
            formatted_reply = "Sorry, something went wrong. Please try again or type 'start over'."
        
        # Return TwiML XML response — Twilio reads this and sends back to the user
        from fastapi.responses import Response
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'<Message>{_escape_xml(formatted_reply)}</Message>'
            '</Response>'
        )
        return Response(content=twiml, media_type="application/xml")
    
    logger.error(f"[WEBHOOK] Invalid content type: {content_type}")
    return {"status": "error", "message": "unsupported"}


def _escape_xml(text: str) -> str:
    """Escape special XML characters in the reply text"""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@router.get("/webhook")
async def verify_webhook(request: Request):
    """WhatsApp webhook verification (GET)"""
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")
    
    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return int(hub_challenge) if hub_challenge else 0
    
    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Invalid verification token")
