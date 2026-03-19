import httpx
import logging

logger = logging.getLogger(__name__)

class WhatsAppInteractiveConfig:
    """External HTTP Wrapper for Meta Cloud API Integrations."""
    
    def __init__(self, token: str, phone_id: str):
        self.url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def send_text(self, to: str, text: str):
        """Standard text fallback for AI responses."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text}
        }
        await self._dispatch(payload)

    async def send_interactive_buttons(self, to: str, text_body: str, buttons: list[dict]):
        """
        Forces zero-typo structured payload from Users.
        `buttons` format: [{"id": "accept", "title": "Accept Job"}]
        """
        formatted_buttons = [
            {
                "type": "reply",
                "reply": {"id": b["id"], "title": b["title"][:20]} # title max 20 chars
            }
            for b in buttons][:3] # Max 3 buttons per message
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text_body},
                "action": {"buttons": formatted_buttons}
            }
        }
        await self._dispatch(payload)

    async def _dispatch(self, payload: dict):
        # We fire these async without blocking execution rules
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, headers=self.headers, json=payload, timeout=5)
                response.raise_for_status()
                logger.info(f"Dispatched message to {payload.get('to')}")
            except Exception as e:
                logger.error(f"Failed to push WhatsApp message: {e}")
