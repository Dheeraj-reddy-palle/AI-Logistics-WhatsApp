import pytest
from unittest.mock import AsyncMock, patch
import uuid
from app.services.driver_service import DriverService
from app.models.driver import Driver, VehicleType

@pytest.fixture
def driver_service(mock_db_session):
    return DriverService(mock_db_session)

@pytest.mark.asyncio
async def test_find_nearby_available_drivers_redis_hit(driver_service, mock_redis, mock_db_session):
    """Simulates Redis GEO indexing returning a fast cached subset of drivers."""
    mock_redis.geosearch.return_value = ["driver_1", "driver_2"]
    
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_driver = Driver(id=uuid.uuid4(), is_available=True)
    # Configure mock chain correctly: mock_result.scalars().all() -> returns list
    mock_result.scalars.return_value.all.return_value = [mock_driver]
    mock_db_session.execute.return_value = mock_result
    
    drivers = await driver_service.find_nearby_available_drivers(
        lat=40.71, lng=-74.0, radius_meters=5000, vehicle_type=VehicleType.CAR
    )
    
    assert len(drivers) == 1
    mock_redis.geosearch.assert_called_once()
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_attempt_assignment_concurrency(driver_service):
    """Test the safety layer of Driver DB assignments (Simulating a Race Condition)."""
    with patch("app.services.driver_service.lock_and_assign_driver", new_callable=AsyncMock) as mock_lock:
        # Simulate that another node snatched the driver exactly at this millisecond
        mock_lock.return_value = None 
        
        assigned = await driver_service.attempt_assignment(uuid.uuid4(), uuid.uuid4())
        
        # Expected none, no exceptions thrown
        assert assigned is None
