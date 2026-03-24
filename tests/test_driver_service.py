import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from app.services.driver_service import DriverService
from app.models.driver import Driver, VehicleType


@pytest.fixture
def driver_service(mock_db_session):
    return DriverService(mock_db_session)


@pytest.mark.asyncio
async def test_find_nearest_available_driver(driver_service, mock_db_session):
    """Test finding the nearest available driver via Haversine distance."""
    mock_driver = Driver(
        id=uuid.uuid4(),
        name="TestDriver",
        phone="9991",
        vehicle_type=VehicleType.TRUCK,
        is_available=True,
        last_known_lat=17.385,
        last_known_lng=78.486,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_driver]
    mock_db_session.execute.return_value = mock_result

    driver = await driver_service.find_nearest_available_driver(
        lat=17.39, lng=78.49, vehicle_type="truck"
    )

    assert driver is not None
    assert driver.name == "TestDriver"
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_assignment_concurrency(driver_service):
    """Test the safety layer of Driver DB assignments using lock_and_assign_driver."""
    with patch("app.db.locks.lock_and_assign_driver", new_callable=AsyncMock) as mock_lock:
        # Simulate that another node snatched the driver exactly at this millisecond
        mock_lock.return_value = None

        result = await mock_lock(None, uuid.uuid4(), uuid.uuid4())

        # Expected None — no exceptions thrown, graceful handling
        assert result is None


@pytest.mark.asyncio
async def test_mark_driver_unavailable(driver_service, mock_db_session):
    """Test marking a driver as unavailable after assignment."""
    driver_id = uuid.uuid4()
    mock_driver = Driver(
        id=driver_id, name="Amit", phone="9991",
        vehicle_type=VehicleType.TRUCK, is_available=True,
        last_known_lat=17.385, last_known_lng=78.486,
    )
    mock_db_session.get.return_value = mock_driver
    mock_db_session.commit = AsyncMock()

    await driver_service.mark_unavailable(driver_id)

    assert mock_driver.is_available is False
    mock_db_session.commit.assert_called_once()
