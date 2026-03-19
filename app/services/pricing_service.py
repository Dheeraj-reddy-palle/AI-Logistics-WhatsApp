from typing import Optional
from decimal import Decimal
from app.services.location_resolver import haversine_distance


class PricingService:
    """
    Local pricing service using Haversine distance + weight-based calculation.
    No external API calls.
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
        - Haversine distance between coordinates
        - Weight-based surcharge
        - Vehicle type multiplier
        
        Returns dict with price and disclaimer.
        """
        # Calculate distance
        distance_km = haversine_distance(pickup_lat, pickup_lng, drop_lat, drop_lng)
        
        # Get vehicle multiplier
        multiplier = PricingService.VEHICLE_MULTIPLIERS.get(
            vehicle_type.lower(), Decimal("1.0")
        )
        
        # Calculate price
        distance_cost = PricingService.RATE_PER_KM * Decimal(str(round(distance_km, 2)))
        weight_cost = PricingService.RATE_PER_KG * Decimal(str(weight_kg))
        total = (PricingService.BASE_FARE + distance_cost + weight_cost) * multiplier
        
        disclaimer = (
            "" if vehicle_type.lower() == "car" 
            else "⚠️ Final price may change after weight verification at pickup."
        )
        
        return {
            "price": round(total, 2),
            "distance_km": round(distance_km, 2),
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
