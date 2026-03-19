import enum
import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Float, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    DRIVER_ASSIGNED = "driver_assigned"
    DRIVER_ACCEPTED = "driver_accepted"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Booking(Base):
    __tablename__ = "bookings"

    customer_phone: Mapped[str] = mapped_column(String(20), index=True)
    
    # Route info (text addresses)
    pickup_address: Mapped[str] = mapped_column(String(500))
    drop_address: Mapped[str] = mapped_column(String(500))
    
    # Precise coordinates
    pickup_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pickup_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drop_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drop_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    vehicle_type: Mapped[str] = mapped_column(String(50), default="truck")

    # Weight tracking (Scenario 4: Weight Fraud)
    declared_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verified_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # State tracking
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING, index=True)
    
    # Driver tracking
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)

    # Remote booking (Scenario 3)
    booked_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    passenger_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Financials
    price_quote: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
