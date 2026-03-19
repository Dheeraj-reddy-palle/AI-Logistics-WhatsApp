import redis.asyncio as redis
import json
from typing import Dict

class StateMachine:
    """
    Manages per-user conversational state in Redis with granular states:
    idle → collecting_pickup → collecting_drop → collecting_weight → 
    collecting_passenger → booking_confirmed → driver_assigned → tracking
    
    Also supports: cancel/reset commands at any point.
    """
    
    VALID_STATES = [
        "idle",
        "collecting_pickup",
        "collecting_drop", 
        "collecting_weight",
        "collecting_passenger",
        "booking_confirmed",
        "driver_assigned",
        "tracking",
    ]
    
    CANCEL_KEYWORDS = ["cancel", "start over", "reset", "restart", "stop", "quit"]
    
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = 3600  # 1 hour state TTL

    def _key(self, phone: str) -> str:
        return f"user:state:{phone}"

    async def get_state(self, phone: str) -> Dict:
        """Fetch full contextual state dict"""
        data = await self.client.get(self._key(phone))
        if data:
            return json.loads(data)
        return self._default_state()
    
    def _default_state(self) -> Dict:
        return {
            "current_flow": "idle",
            "context": {
                "pickup": None,
                "pickup_lat": None,
                "pickup_lng": None,
                "drop": None,
                "drop_lat": None,
                "drop_lng": None,
                "weight": None,
                "vehicle_type": "truck",
                "is_remote": False,
                "passenger_phone": None,
                "booked_by": None,
                "booking_id": None,
            }
        }

    async def update_state(self, phone: str, new_flow: str, context_updates: dict = None):
        """Advances or updates the state machine"""
        current = await self.get_state(phone)
        current["current_flow"] = new_flow
        if context_updates:
            current["context"].update(context_updates)
            
        state_str = json.dumps(current)
        await self.client.setex(
            self._key(phone), 
            self.ttl_seconds, 
            state_str
        )

    async def clear_state(self, phone: str):
        """Resets conversation to idle (e.g., after booking complete or cancel)"""
        await self.client.delete(self._key(phone))

    async def check_idempotency(self, message_id: str) -> bool:
        """
        Returns True if the message is NEW (not yet processed).
        Returns False if duplicate (already seen).
        Uses Redis SETNX for atomic check-and-set.
        """
        key = f"msg:{message_id}"
        # SETNX returns True if key did NOT exist (new message)
        is_new = await self.client.set(key, "1", nx=True, ex=86400)  # 24h TTL
        return bool(is_new)
    
    def is_cancel_command(self, text: str) -> bool:
        """Check if user wants to cancel/reset current flow"""
        text_lower = text.strip().lower()
        return any(kw in text_lower for kw in self.CANCEL_KEYWORDS)

    # --- Driver tracking helpers ---
    
    async def store_driver_location(self, booking_id: str, lat: float, lng: float):
        """Store driver's latest location in Redis for live tracking"""
        key = f"tracking:{booking_id}"
        data = json.dumps({"lat": lat, "lng": lng})
        await self.client.setex(key, 3600, data)  # 1h TTL
    
    async def get_driver_location(self, booking_id: str) -> Dict:
        """Fetch driver's latest location from Redis"""
        key = f"tracking:{booking_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
