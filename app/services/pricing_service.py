from typing import Optional
from decimal import Decimal
import httpx
import logging
from app.services.location_resolver import haversine_distance

logger = logging.getLogger(__name__)


def _get_osrm_route(pickup_lat: float, pickup_lng: float, drop_lat: float, drop_lng: float) -> dict:
    """Get real driving distance and duration from OSRM (free, no API key needed).
    Returns {distance_km, duration_min} or None if API fails."""
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{pickup_lng},{pickup_lat};{drop_lng},{drop_lat}"
            f"?overview=false"
        )
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_km = round(route["distance"] / 1000, 2)  # meters -> km
                    duration_min = round(route["duration"] / 60, 1)    # seconds -> minutes
                    logger.info(f"OSRM route: {distance_km}km, {duration_min}min")
                    return {"distance_km": distance_km, "duration_min": duration_min}
    except Exception as e:
        logger.warning(f"OSRM routing failed: {e}")
    return None


class PricingService:
    """
    Pricing service using OSRM real road distance + weight-based calculation.
    Falls back to Haversine if OSRM is unavailable.
    """
    
    # Rate constants (configurable)
    BASE_FARE = Decimal("50.00")          # Base fare in currency units
    RATE_PER_KM = Decimal("15.00")        # Rate per kilometer
    RATE_PER_KG = Decimal("2.00")         # Rate per kg of weight
    
    VEHICLE_MULTIPLIERS = {
        "motorcycle": Decimal("0.8"),
        "car": Decimal("1.0"),
        "van": Decimal("1.5"),
        "truck": Decimal("2.0"),
    }
    
    @staticmethod
    def generate_quote(
        pickup_lat: float, pickup_lng: float,
        drop_lat: float, drop_lng: float,
        weight_kg: float,
        vehicle_type: str = "truck"
    ) -> dict:
        """
        Calculate price quote using:
        - OSRM real road distance (fallback: Haversine × 1.3)
        - Weight-based surcharge
        - Vehicle type multiplier
        
        Returns dict with price, distance, duration, and disclaimer.
        """
        # Get real road distance from OSRM
        osrm = _get_osrm_route(pickup_lat, pickup_lng, drop_lat, drop_lng)
        
        if osrm:
            distance_km = osrm["distance_km"]
            duration_min = osrm["duration_min"]
        else:
            # Fallback: Haversine × 1.3 (roads are ~30% longer than straight line)
            straight_line = haversine_distance(pickup_lat, pickup_lng, drop_lat, drop_lng)
            distance_km = round(straight_line * 1.3, 2)
            duration_min = round(distance_km / 30 * 60, 1)  # rough estimate at 30 km/h avg
            logger.warning(f"Using Haversine fallback: {distance_km}km (straight: {straight_line}km)")
        
        # Get vehicle multiplier
        multiplier = PricingService.VEHICLE_MULTIPLIERS.get(
            vehicle_type.lower(), Decimal("1.0")
        )
        
        # Calculate price
        distance_cost = PricingService.RATE_PER_KM * Decimal(str(distance_km))
        weight_cost = PricingService.RATE_PER_KG * Decimal(str(weight_kg))
        total = (PricingService.BASE_FARE + distance_cost + weight_cost) * multiplier
        
        disclaimer = (
            "" if vehicle_type.lower() == "car" 
            else "⚠️ Final price may change after weight verification at pickup."
        )
        
        return {
            "price": round(total, 2),
            "distance_km": distance_km,
            "duration_min": duration_min,
            "weight_kg": weight_kg,
            "vehicle_type": vehicle_type,
            "disclaimer": disclaimer,
        }
    
    @staticmethod
    def recalculate_with_verified_weight(
        original_quote: Decimal,
        declared_weight: float,
        verified_weight: float,
        pickup_lat: float, pickup_lng: float,
        drop_lat: float, drop_lng: float,
        vehicle_type: str = "truck"
    ) -> dict:
        """
        Recalculate price when driver verifies weight differs from declared.
        """
        if abs(declared_weight - verified_weight) < 0.5:
            # Negligible difference
            return {
                "recalculated": False,
                "final_price": original_quote,
                "message": "Weight verified. No change in price.",
            }
        
        # Full recalculation with verified weight
        new_quote = PricingService.generate_quote(
            pickup_lat, pickup_lng,
            drop_lat, drop_lng,
            verified_weight,
            vehicle_type
        )
        
        weight_diff = verified_weight - declared_weight
        direction = "higher" if weight_diff > 0 else "lower"
        
        return {
            "recalculated": True,
            "original_price": float(original_quote),
            "final_price": float(new_quote["price"]),
            "declared_weight": declared_weight,
            "verified_weight": verified_weight,
            "weight_difference": round(abs(weight_diff), 2),
            "message": f"⚠️ Weight is {round(abs(weight_diff), 2)}kg {direction} than declared. Price updated from ₹{original_quote} to ₹{new_quote['price']}.",
        }
