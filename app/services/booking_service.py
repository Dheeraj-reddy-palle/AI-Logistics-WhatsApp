import uuid
import logging
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.booking import Booking, BookingStatus

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_booking(self, booking_id: uuid.UUID) -> Optional[Booking]:
        return await self.session.get(Booking, booking_id)

    async def create_booking(
        self,
        customer_phone: str,
        pickup_address: str,
        drop_address: str,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        declared_weight: float,
        vehicle_type: str = "truck",
        price_quote: Decimal = Decimal("0"),
        booked_by: str = None,
        passenger_phone: str = None,
    ) -> Booking:
        """
        Creates a PENDING booking in the database.
        """
        booking = Booking(
            customer_phone=customer_phone,
            pickup_address=pickup_address,
            drop_address=drop_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            drop_lat=drop_lat,
            drop_lng=drop_lng,
            declared_weight=declared_weight,
            vehicle_type=vehicle_type,
            price_quote=price_quote,
            booked_by=booked_by or customer_phone,
            passenger_phone=passenger_phone,
            status=BookingStatus.PENDING,
        )
        self.session.add(booking)
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def get_active_booking_for_customer(self, phone: str) -> Optional[Booking]:
        """Fetch the most recent active booking for a customer"""
        stmt = (
            select(Booking)
            .where(
                (Booking.customer_phone == phone) | (Booking.booked_by == phone)
            )
            .where(
                Booking.status.in_([
                    BookingStatus.PENDING,
                    BookingStatus.DRIVER_ASSIGNED,
                    BookingStatus.DRIVER_ACCEPTED,
                    BookingStatus.PICKED_UP,
                    BookingStatus.IN_TRANSIT,
                ])
            )
            .order_by(Booking.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_verified_weight(
        self, booking_id: uuid.UUID, verified_weight: float
    ) -> Optional[Booking]:
        """
        Updates the verified weight on a booking.
        Called by driver after physical verification at pickup.
        """
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            return None

        booking.verified_weight = verified_weight
        
        # Recalculate price if weight mismatch
        if booking.declared_weight and abs(booking.declared_weight - verified_weight) >= 0.5:
            from app.services.pricing_service import PricingService
            result = PricingService.recalculate_with_verified_weight(
                original_quote=booking.price_quote,
                declared_weight=booking.declared_weight,
                verified_weight=verified_weight,
                pickup_lat=booking.pickup_lat,
                pickup_lng=booking.pickup_lng,
                drop_lat=booking.drop_lat,
                drop_lng=booking.drop_lng,
                vehicle_type=booking.vehicle_type,
            )
            if result["recalculated"]:
                booking.final_price = Decimal(str(result["final_price"]))
                logger.info(f"Price recalculated for booking {booking_id}: {result['message']}")
        else:
            booking.final_price = booking.price_quote

        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def assign_driver(self, booking_id: uuid.UUID, driver_id: uuid.UUID) -> Optional[Booking]:
        """Assign a driver to a booking"""
        booking = await self.session.get(Booking, booking_id)
        if not booking or booking.status != BookingStatus.PENDING:
            return None
        
        booking.driver_id = driver_id
        booking.status = BookingStatus.DRIVER_ASSIGNED
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def accept_booking(self, booking_id: uuid.UUID, driver_id: uuid.UUID) -> Optional[Booking]:
        """Mark booking as accepted by driver"""
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            return None
        if booking.driver_id != driver_id:
            return None
        if booking.status != BookingStatus.DRIVER_ASSIGNED:
            return None
        
        booking.status = BookingStatus.DRIVER_ACCEPTED
        await self.session.commit()
        await self.session.refresh(booking)
        return booking
