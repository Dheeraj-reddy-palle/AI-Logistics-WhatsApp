import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import List, Optional

from app.models.driver import Driver, VehicleType
from app.services.location_resolver import haversine_distance

logger = logging.getLogger(__name__)


class DriverService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_nearest_available_driver(
        self,
        lat: float,
        lng: float,
        vehicle_type: str = None,
    ) -> Optional[Driver]:
        """
        Find the nearest available driver using simple distance calculation.
        No PostGIS required — uses Haversine on plain lat/lng.
        """
        stmt = select(Driver).where(Driver.is_available == True)
        if vehicle_type:
            try:
                vt = VehicleType(vehicle_type)
                stmt = stmt.where(Driver.vehicle_type == vt)
            except ValueError:
                pass  # Ignore invalid vehicle type filter
        
        result = await self.session.execute(stmt)
        available_drivers = list(result.scalars().all())
        
        if not available_drivers:
            return None
        
        # Sort by distance using Haversine
        def driver_distance(driver):
            if driver.last_known_lat is None or driver.last_known_lng is None:
                return float('inf')
            return haversine_distance(lat, lng, driver.last_known_lat, driver.last_known_lng)
        
        available_drivers.sort(key=driver_distance)
        return available_drivers[0]

    async def get_driver(self, driver_id: uuid.UUID) -> Optional[Driver]:
        """Get driver by ID"""
        return await self.session.get(Driver, driver_id)
    
    async def get_driver_by_phone(self, phone: str) -> Optional[Driver]:
        """Get driver by phone"""
        stmt = select(Driver).where(Driver.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def mark_unavailable(self, driver_id: uuid.UUID):
        """Mark driver as unavailable after assignment"""
        driver = await self.session.get(Driver, driver_id)
        if driver:
            driver.is_available = False
            await self.session.commit()

    async def mark_available(self, driver_id: uuid.UUID):
        """Mark driver as available after delivery complete"""
        driver = await self.session.get(Driver, driver_id)
        if driver:
            driver.is_available = True
            await self.session.commit()

    async def update_location(self, driver_id: uuid.UUID, lat: float, lng: float):
        """Update driver location in database"""
        driver = await self.session.get(Driver, driver_id)
        if driver:
            driver.last_known_lat = lat
            driver.last_known_lng = lng
            await self.session.commit()
