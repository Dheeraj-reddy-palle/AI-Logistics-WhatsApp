"""
Security middleware — simplified for local dev mode.
In production, this would validate Meta webhook signatures and apply rate limiting.
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # In dev mode, skip all security checks for easy testing
        if settings.ENV == "dev":
            response = await call_next(request)
            return response
        
        # Production: validate Meta webhook signatures
        if request.method == "POST" and "/webhook" in request.url.path:
            import hashlib
            import hmac
            
            signature = request.headers.get("x-hub-signature-256")
            if not signature:
                return JSONResponse(status_code=403, content={"detail": "Missing Signature"})
            
            body = await request.body()
            verify_token = settings.WEBHOOK_VERIFY_TOKEN or ""
            expected = "sha256=" + hmac.new(
                verify_token.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected, signature):
                return JSONResponse(status_code=403, content={"detail": "Invalid Signature"})
        
        response = await call_next(request)
        return response
