class MapsIntegration:
    """Mock interface to validate geographic boundaries via Google Maps."""
    @staticmethod
    async def get_distance_matrix(origin: str, destination: str) -> dict:
        return {"distance_meters": 15000, "duration_seconds": 1800}

    @staticmethod
    async def reverse_geocode(lat: float, lng: float) -> str:
        return "123 Delivery Ln, New York, NY 10001"
