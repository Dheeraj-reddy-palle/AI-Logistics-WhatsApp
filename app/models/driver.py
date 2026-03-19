import enum
from typing import Optional
from sqlalchemy import String, Boolean, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class VehicleType(str, enum.Enum):
    MOTORCYCLE = "motorcycle"
    CAR = "car"
    VAN = "van"
    TRUCK = "truck"

class Driver(Base):
    __tablename__ = "drivers"

    name: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(Enum(VehicleType))
    
    # Simple lat/lng (no PostGIS dependency)
    last_known_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_known_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
