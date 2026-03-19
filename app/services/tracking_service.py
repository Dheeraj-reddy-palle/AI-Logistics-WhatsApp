import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.booking import Booking, BookingStatus
from app.services.location_resolver import generate_tracking_link

logger = logging.getLogger(__name__)


class TrackingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_booking_status(self, booking_id: uuid.UUID) -> Optional[dict]:
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            return None
        return {
            "booking_id": str(booking.id),
            "status": booking.status.value,
            "pickup": booking.pickup_address,
            "drop": booking.drop_address,
        }

    async def update_status(self, booking_id: uuid.UUID, new_status: BookingStatus) -> Optional[Booking]:
        """Updates the booking status."""
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            return None
        booking.status = new_status
        await self.session.commit()
        await self.session.refresh(booking)
        return booking
    
    @staticmethod
    def get_tracking_link(lat: float, lng: float) -> str:
        """Generate a Google Maps tracking link from driver coordinates"""
        return generate_tracking_link(lat, lng)
    
    @staticmethod
    def format_tracking_message(lat: float, lng: float) -> str:
        """Format a tracking update message for the customer"""
        link = generate_tracking_link(lat, lng)
        return f"📍 Driver is on the way!\nLive location: {link}"
    
    @staticmethod
    def no_location_message() -> str:
        """Fallback when no driver location available (Correction #6)"""
        return "📍 Driver location not available yet. Please check back shortly."
