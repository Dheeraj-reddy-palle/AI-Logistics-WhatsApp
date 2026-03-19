import re
import math
import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class LocationResult:
    """Result from location resolution"""
    lat: Optional[float] = None
    lng: Optional[float] = None
    precision: str = "low"  # "exact" or "low"
    display_name: str = ""
    raw_input: str = ""


# Known locations database (expandable)
# precision: "exact" = can be used directly, "low" = need clarification
KNOWN_LOCATIONS = {
    # Airports (exact)
    "rgia": {"lat": 17.2403, "lng": 78.4294, "precision": "exact", "name": "RGIA (Rajiv Gandhi Intl Airport)"},
    "rajiv gandhi airport": {"lat": 17.2403, "lng": 78.4294, "precision": "exact", "name": "RGIA"},
    "shamshabad airport": {"lat": 17.2403, "lng": 78.4294, "precision": "exact", "name": "RGIA Shamshabad"},
    "delhi airport": {"lat": 28.5562, "lng": 77.1000, "precision": "exact", "name": "IGI Airport Delhi"},
    "igi airport": {"lat": 28.5562, "lng": 77.1000, "precision": "exact", "name": "IGI Airport Delhi"},
    "mumbai airport": {"lat": 19.0896, "lng": 72.8656, "precision": "exact", "name": "Mumbai Airport"},
    
    # Railway stations (exact)
    "secunderabad station": {"lat": 17.4344, "lng": 78.5013, "precision": "exact", "name": "Secunderabad Railway Station"},
    "hyderabad station": {"lat": 17.3850, "lng": 78.4867, "precision": "exact", "name": "Hyderabad Railway Station"},
    "new delhi station": {"lat": 28.6424, "lng": 77.2195, "precision": "exact", "name": "New Delhi Railway Station"},
    
    # Areas (low precision - need clarification)
    "kondapur": {"lat": 17.4632, "lng": 78.3571, "precision": "low", "name": "Kondapur Area"},
    "dilsukhnagar": {"lat": 17.3687, "lng": 78.5247, "precision": "low", "name": "Dilsukhnagar Area"},
    "ameerpet": {"lat": 17.4375, "lng": 78.4483, "precision": "low", "name": "Ameerpet Area"},
    "banjara hills": {"lat": 17.4156, "lng": 78.4347, "precision": "low", "name": "Banjara Hills Area"},
    "jubilee hills": {"lat": 17.4325, "lng": 78.4073, "precision": "low", "name": "Jubilee Hills Area"},
    "hitech city": {"lat": 17.4435, "lng": 78.3772, "precision": "low", "name": "Hitech City Area"},
    "gachibowli": {"lat": 17.4401, "lng": 78.3489, "precision": "low", "name": "Gachibowli Area"},
    "madhapur": {"lat": 17.4484, "lng": 78.3908, "precision": "low", "name": "Madhapur Area"},
    "kukatpally": {"lat": 17.4849, "lng": 78.4138, "precision": "low", "name": "Kukatpally Area"},
    "miyapur": {"lat": 17.4969, "lng": 78.3565, "precision": "low", "name": "Miyapur Area"},
    "uppal": {"lat": 17.4000, "lng": 78.5600, "precision": "low", "name": "Uppal Area"},
    "lb nagar": {"lat": 17.3488, "lng": 78.5514, "precision": "low", "name": "LB Nagar Area"},
    "delhi": {"lat": 28.7041, "lng": 77.1025, "precision": "low", "name": "Delhi"},
    "mumbai": {"lat": 19.0760, "lng": 72.8777, "precision": "low", "name": "Mumbai"},
    "bangalore": {"lat": 12.9716, "lng": 77.5946, "precision": "low", "name": "Bangalore"},
    "chennai": {"lat": 13.0827, "lng": 80.2707, "precision": "low", "name": "Chennai"},
}

# Regex for Google Maps link
MAPS_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:google\.com/maps|maps\.google\.com|maps\.app\.goo\.gl|goo\.gl/maps)[^\s]*[?&/@](-?\d+\.?\d*)[,/](-?\d+\.?\d*)',
    re.IGNORECASE
)

# Regex for raw lat,lng coordinates
COORD_PATTERN = re.compile(
    r'(-?\d{1,3}\.\d{2,8})\s*[,\s]\s*(-?\d{1,3}\.\d{2,8})'
)

# Simplified Google Maps short link with @lat,lng
MAPS_AT_PATTERN = re.compile(
    r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
)


def _expand_shortlink(url: str) -> str:
    """Expand shortlinks like maps.app.goo.gl and extract best URL or Title"""
    try:
        with httpx.Client(follow_redirects=True, timeout=5.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) AppleWebKit/605.1.15 Chrome/91.0",
                "Accept-Language": "en-US,en;q=0.9"
            }
            response = client.get(url, headers=headers)
            
            urls = [url] + [str(r.headers.get("Location", "")) for r in response.history] + [str(r.url) for r in response.history] + [str(response.url)]
            
            for u in urls:
                if "@" in u or "?q=" in u or "&q=" in u or "ll=" in u or "query=" in u:
                    return u
                    
            text = response.text
            match = re.search(r'center=(-?\d+\.\d+)[,%C2]+(-?\d+\.\d+)', text)
            if match:
                return f"https://maps.google.com/?q={match.group(1)},{match.group(2)}"
            
            # If coordinates are masked, extract the exact Place name from HTML title
            title_match = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).replace("- Google Maps", "").replace("Google Maps", "").strip()
                if title:
                    return f"GEOCODE_TITLE:{title}"
                
            return urls[-1]
    except Exception as e:
        return url


def _geocode_address(text: str, result: LocationResult) -> bool:
    """Fallback: Free Text Geocoding via OpenStreetMap (Nominatim)"""
    try:
        if len(text) < 3:
            return False
            
        with httpx.Client(timeout=4.0) as client:
            headers = {"User-Agent": "AILogisticsApp/1.0"}
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": text, "format": "json", "limit": 1},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    best = data[0]
                    result.lat = float(best["lat"])
                    result.lng = float(best["lon"])
                    result.precision = "exact"
                    
                    raw_name = best.get("display_name", text)
                    parts = raw_name.split(",")
                    if len(parts) > 2:
                        clean_name = f"{parts[0].strip()}, {parts[-1].strip()}"
                    else:
                        clean_name = raw_name
                        
                    result.display_name = clean_name
                    return True
    except Exception:
        pass
    return False


def resolve_location(text: str) -> LocationResult:
    """
    Resolve a location string to coordinates.
    Priority: shortlink expansion > @ coordinates > ?q= coordinates > raw > known > geocode
    """
    text = text.strip()
    result = LocationResult(raw_input=text)
    
    # Check for direct TITLE intercept from prior passes
    extracted_title = ""
    
    # 0. Expand shortlinks if present
    shortlink_match = re.search(r'(https?://(?:maps\.app\.goo\.gl|goo\.gl/maps|maps\.google\.com/)[^\s]+)', text)
    if shortlink_match:
        url = shortlink_match.group(1)
        expanded = _expand_shortlink(url)
        if expanded.startswith("GEOCODE_TITLE:"):
            extracted_title = expanded.replace("GEOCODE_TITLE:", "")
            text = text.replace(url, extracted_title)
        else:
            text = text.replace(url, expanded)
    
    # 1. Try @lat,lng pattern (matches expanded Google Maps URLs)
    match = MAPS_AT_PATTERN.search(text)
    if match:
        result.lat = float(match.group(1))
        result.lng = float(match.group(2))
        result.precision = "exact"
        result.display_name = f"Maps Location ({result.lat}, {result.lng})"
        return result
    
    import urllib.parse
    
    # 2. Try ?q=lat,lng pattern OR extract physical address from q= attribute
    q_match = re.search(r'[?&](?:q|ll|query)=([^&]+)', text)
    if q_match:
        q_val = urllib.parse.unquote_plus(q_match.group(1))
        # Check if the extracted query is a coordinate pair
        coord_match = re.search(r'^(-?\d+\.\d+)[,\sC2%]+(-?\d+\.\d+)$', q_val)
        if coord_match:
            result.lat = float(coord_match.group(1))
            result.lng = float(coord_match.group(2))
            result.precision = "exact"
            result.display_name = f"Maps Location ({result.lat}, {result.lng})"
            return result
        else:
            # The query is a physical text address (e.g., "1st St, San Francisco")
            # Replace `text` so the URL stripper ignores it and it cascades straight to Nominatim Geocoder!
            text = q_val
        
    # 3. Try legacy Maps Link Pattern just in case
    match = MAPS_LINK_PATTERN.search(text)
    if match:
        result.lat = float(match.group(1))
        result.lng = float(match.group(2))
        result.precision = "exact"
        result.display_name = f"Maps Location ({result.lat}, {result.lng})"
        return result
    
    # Strip lingering URLs so geocoder doesn't fail parsing raw queries
    clean_text = re.sub(r'https?://[^\s]+', '', text).strip()
    
    # 4. Try raw coordinates
    match = COORD_PATTERN.search(clean_text)
    if match:
        lat = float(match.group(1))
        lng = float(match.group(2))
        # Sanity check: lat between -90 and 90, lng between -180 and 180
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            result.lat = lat
            result.lng = lng
            result.precision = "exact"
            result.display_name = f"Coordinates ({lat}, {lng})"
            return result
    
    # 5. Lookup in known locations
    text_lower = clean_text.lower()
    if text_lower and text_lower in KNOWN_LOCATIONS:
        loc = KNOWN_LOCATIONS[text_lower]
        result.lat = float(loc["lat"])
        result.lng = float(loc["lng"])
        result.precision = str(loc["precision"])
        result.display_name = str(loc["name"])
        return result
    
    # 6. Partial match in known locations
    if len(text_lower) >= 3:
        for key, loc in KNOWN_LOCATIONS.items():
            if key in text_lower or text_lower in key:
                result.lat = float(loc["lat"])
                result.lng = float(loc["lng"])
                result.precision = str(loc["precision"])
                result.display_name = str(loc["name"])
                return result
            
    # 7. Fallback to Free Text Geocoding (Nominatim API)
    if clean_text and _geocode_address(clean_text, result):
        return result
    
    # 8. Unknown location
    result.precision = "low"
    result.display_name = text
    return result


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points on Earth using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def generate_tracking_link(lat: float, lng: float) -> str:
    """Generate a Google Maps tracking link from coordinates"""
    return f"https://maps.google.com/?q={lat},{lng}"
