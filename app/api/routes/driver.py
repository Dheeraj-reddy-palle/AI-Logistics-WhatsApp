"""
Driver API routes for:
- Accepting bookings
- Updating location (live tracking)
- Verifying weight (fraud detection)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import logging

from app.db.session import AsyncSessionLocal
from app.services.booking_service import BookingService
from app.services.driver_service import DriverService
from app.services.tracking_service import TrackingService
from app.services.location_resolver import generate_tracking_link
from app.ai.state_machine import StateMachine
from app.config.settings import settings

router = APIRouter(prefix="/driver", tags=["Driver"])
logger = logging.getLogger(__name__)

state_manager = StateMachine(redis_url=settings.REDIS_URL)


class DriverAcceptPayload(BaseModel):
    driver_id: str
    booking_id: str


class DriverLocationPayload(BaseModel):
    driver_id: str
    booking_id: str
    lat: float
    lng: float


class VerifyWeightPayload(BaseModel):
    driver_id: str
    booking_id: str
    verified_weight: float


@router.post("/accept")
async def driver_accept_booking(payload: DriverAcceptPayload):
    """
    Driver accepts a booking assignment.
    After acceptance: exchange driver ↔ customer info (Scenario 5).
    Validates booking exists, driver exists, and driver is assigned (Correction #9).
    """
    try:
        driver_uuid = uuid.UUID(payload.driver_id)
        booking_uuid = uuid.UUID(payload.booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    async with AsyncSessionLocal() as session:
        booking_svc = BookingService(session)
        driver_svc = DriverService(session)
        
        # Validate booking exists (Correction #9)
        booking = await booking_svc.get_booking(booking_uuid)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Validate driver exists (Correction #9)
        driver = await driver_svc.get_driver(driver_uuid)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        # Validate driver is assigned to this booking (Correction #9)
        if booking.driver_id != driver_uuid:
            raise HTTPException(status_code=400, detail="Driver not assigned to this booking")
        
        # Accept the booking
        accepted_booking = await booking_svc.accept_booking(booking_uuid, driver_uuid)
        if not accepted_booking:
            raise HTTPException(status_code=400, detail="Booking cannot be accepted (wrong status)")
        
        # SCENARIO 5: Exchange info between driver and customer
        customer_phone = booking.passenger_phone or booking.customer_phone
        
        # Info sent to customer
        customer_info_msg = (
            f"✅ Driver accepted your booking!\n\n"
            f"🚛 Driver: {driver.name}\n"
            f"📱 Phone: {driver.phone}\n"
            f"🚗 Vehicle: {driver.vehicle_type.value.title()}\n"
            f"📋 Booking: {str(booking.id)[:8]}"
        )
        
        # Info sent to driver
        driver_info_msg = (
            f"✅ You accepted booking #{str(booking.id)[:8]}!\n\n"
            f"👤 Customer: {customer_phone}\n"
            f"📍 Pickup: {booking.pickup_address}\n"
            f"📍 Drop: {booking.drop_address}\n"
            f"📦 Weight: {booking.declared_weight}kg"
        )
        
        # Log mock WhatsApp messages
        logger.info(f">>> [MOCK WHATSAPP TO CUSTOMER {customer_phone}]: {customer_info_msg}")
        logger.info(f">>> [MOCK WHATSAPP TO DRIVER {driver.phone}]: {driver_info_msg}")
        
        return {
            "status": "accepted",
            "booking_id": str(booking.id),
            "customer_message": customer_info_msg,
            "driver_message": driver_info_msg,
            "driver_info": {
                "name": driver.name,
                "phone": driver.phone,
                "vehicle": driver.vehicle_type.value,
            },
            "customer_info": {
                "phone": customer_phone,
                "pickup": booking.pickup_address,
                "drop": booking.drop_address,
                "weight": booking.declared_weight,
            },
        }


@router.post("/location")
async def driver_location_update(payload: DriverLocationPayload):
    """
    Driver sends live location update (Scenario 6).
    Stores in Redis, generates tracking link.
    Validates driver and booking (Correction #9).
    """
    try:
        driver_uuid = uuid.UUID(payload.driver_id)
        booking_uuid = uuid.UUID(payload.booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Validate lat/lng
    if not (-90 <= payload.lat <= 90) or not (-180 <= payload.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    async with AsyncSessionLocal() as session:
        booking_svc = BookingService(session)
        driver_svc = DriverService(session)
        
        # Validate booking exists (Correction #9)
        booking = await booking_svc.get_booking(booking_uuid)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Validate driver exists (Correction #9)
        driver = await driver_svc.get_driver(driver_uuid)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        # Validate driver is assigned to booking (Correction #9)
        if booking.driver_id != driver_uuid:
            raise HTTPException(status_code=400, detail="Driver not assigned to this booking")
        
        # Store location in Redis
        await state_manager.store_driver_location(str(booking_uuid), payload.lat, payload.lng)
        
        # Update driver's DB location
        await driver_svc.update_location(driver_uuid, payload.lat, payload.lng)
        
        # Generate tracking link
        tracking_link = generate_tracking_link(payload.lat, payload.lng)
        tracking_msg = TrackingService.format_tracking_message(payload.lat, payload.lng)
        
        # Log mock WhatsApp to customer
        customer_phone = booking.passenger_phone or booking.customer_phone
        logger.info(f">>> [MOCK WHATSAPP TO CUSTOMER {customer_phone}]: {tracking_msg}")
        
        return {
            "status": "location_updated",
            "booking_id": str(booking.id),
            "tracking_link": tracking_link,
            "customer_message": tracking_msg,
        }


@router.post("/verify-weight")
async def driver_verify_weight(payload: VerifyWeightPayload):
    """
    Driver reports actual verified weight after pickup (Scenario 4).
    If mismatch with declared weight → recalculates price.
    Validates inputs (Corrections #8, #9).
    """
    try:
        driver_uuid = uuid.UUID(payload.driver_id)
        booking_uuid = uuid.UUID(payload.booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Validate weight (Correction #8)
    if payload.verified_weight <= 0:
        raise HTTPException(status_code=400, detail="Weight must be positive")
    if payload.verified_weight > 50000:
        raise HTTPException(status_code=400, detail="Weight exceeds maximum limit")
    
    async with AsyncSessionLocal() as session:
        booking_svc = BookingService(session)
        driver_svc = DriverService(session)
        
        # Validate booking exists (Correction #9)
        booking = await booking_svc.get_booking(booking_uuid)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Validate driver exists (Correction #9)
        driver = await driver_svc.get_driver(driver_uuid)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        # Validate driver is assigned (Correction #9)
        if booking.driver_id != driver_uuid:
            raise HTTPException(status_code=400, detail="Driver not assigned to this booking")
        
        # Update verified weight (triggers recalculation if mismatch)
        updated_booking = await booking_svc.update_verified_weight(
            booking_uuid, payload.verified_weight
        )
        
        if not updated_booking:
            raise HTTPException(status_code=404, detail="Booking not found for weight update")
        
        # Build response
        weight_diff = abs((updated_booking.declared_weight or 0) - payload.verified_weight)
        recalculated = weight_diff >= 0.5
        
        customer_phone = booking.passenger_phone or booking.customer_phone
        
        if recalculated:
            msg = (
                f"⚠️ Weight verification update!\n"
                f"Declared: {updated_booking.declared_weight}kg\n"
                f"Verified: {payload.verified_weight}kg\n"
                f"Original price: ₹{updated_booking.price_quote}\n"
                f"Updated price: ₹{updated_booking.final_price}"
            )
        else:
            msg = (
                f"✅ Weight verified: {payload.verified_weight}kg\n"
                f"No change in price: ₹{updated_booking.price_quote}"
            )
        
        logger.info(f">>> [MOCK WHATSAPP TO CUSTOMER {customer_phone}]: {msg}")
        
        return {
            "status": "weight_verified",
            "booking_id": str(updated_booking.id),
            "declared_weight": updated_booking.declared_weight,
            "verified_weight": payload.verified_weight,
            "recalculated": recalculated,
            "original_price": float(updated_booking.price_quote) if updated_booking.price_quote else 0,
            "final_price": float(updated_booking.final_price) if updated_booking.final_price else 0,
            "customer_message": msg,
        }
