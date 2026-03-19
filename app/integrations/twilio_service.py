import logging
from twilio.rest import Client
from app.config.settings import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(to: str, message: str) -> bool:
    """Sends a WhatsApp message via Twilio Sandbox"""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured in .env. Skipping WhatsApp transmission.")
        return False
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Twilio requires strict 'whatsapp:' prefixing
        recipient = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
            
        client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=recipient
        )
        logger.info(f">>> [TWILIO WHATSAPP SENT TO {recipient}]: {message[:100]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to send Twilio WhatsApp message to {to}: {e}")
        return False
