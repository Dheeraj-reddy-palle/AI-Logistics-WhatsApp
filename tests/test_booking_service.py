import pytest
from unittest.mock import AsyncMock
from decimal import Decimal
import uuid
from app.services.booking_service import BookingService
from app.models.booking import BookingStatus

@pytest.fixture
def booking_service(mock_db_session):
    return BookingService(mock_db_session)

@pytest.mark.asyncio
async def test_create_booking_success(booking_service, mock_db_session):
    """Test standard booking generation and DB insertion."""
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    
    booking = await booking_service.create_booking(
        customer_phone="1234567890",
        pickup_address="Warehouse A",
        drop_address="Port B",
        weight_kg=150.0,
        vehicle_type="truck",
        price_quote=Decimal("125.00")
    )
    
    assert booking.pickup_address == "Warehouse A"
    assert booking.status == BookingStatus.PENDING
    assert booking.price_quote == Decimal("125.00")
    
    mock_db_session.add.assert_called_once_with(booking)
    mock_db_session.commit.assert_called_once()

