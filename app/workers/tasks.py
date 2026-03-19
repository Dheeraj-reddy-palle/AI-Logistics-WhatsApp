import asyncio
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def send_to_dlq(self, message_id: str, phone_number: str, error_details: str):
    """
    DEAD LETTER QUEUE TASK.
    Saves failed payload for admin review.
    """
    logger.error(f"[DLQ] CRITICAL: Abandoning msg {message_id} from {phone_number}. Err: {error_details}")
    import redis
    from app.config.settings import settings
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.lpush("system:dlq:ai_failures", f"{message_id}::{phone_number}::{error_details}")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_whatsapp_ai_request(self, phone_number: str, message_text: str, message_id: str):
    """
    Background worker for production mode.
    In dev mode, messages are processed synchronously by the webhook route.
    """
    logger.info(f"Processing background WhatsApp request for {phone_number} (MsgID: {message_id})")
    
    from app.ai.agent import handle_incoming_message
    
    try:
        result = asyncio.run(handle_incoming_message(phone_number, message_text, message_id))
        logger.info(f">>> [CELERY RESULT TO {phone_number}]: {result['reply']}")
        
    except Exception as exc:
        logger.error(f"Failed to process WhatsApp request '{message_id}': {exc}")
        
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries exhausted for {message_id}. Pushing to DLQ.")
            send_to_dlq.delay(message_id, phone_number, str(exc))
            
        raise self.retry(exc=exc)
