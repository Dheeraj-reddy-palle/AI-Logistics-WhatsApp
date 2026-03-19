from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import Optional

from app.models.driver import Driver
from app.models.booking import Booking, BookingStatus


async def lock_and_assign_driver(session: AsyncSession, booking_id: uuid.UUID, driver_id: uuid.UUID) -> Optional[Booking]:
    """
    Safely assigns a driver to a booking under a strict database lock.
    Uses SELECT ... FOR UPDATE to avoid double assignments.
    """
    # 1. Lock the booking row
    result = await session.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    booking = result.scalars().first()
    
    if not booking or booking.status != BookingStatus.PENDING:
        return None

    # 2. Lock the driver row
    driver_result = await session.execute(
        select(Driver).where(Driver.id == driver_id).with_for_update()
    )
    driver = driver_result.scalars().first()
    
    if not driver or not driver.is_available:
        return None

    # 3. Perform assignment
    booking.driver_id = driver.id
    booking.status = BookingStatus.DRIVER_ASSIGNED
    driver.is_available = False

    await session.commit()
    await session.refresh(booking)
    return booking
