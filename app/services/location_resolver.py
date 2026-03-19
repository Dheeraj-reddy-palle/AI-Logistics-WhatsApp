import re
import math
import httpx
import urllib.parse
from typing import Optional
from dataclasses import dataclass
import logging

try:
    from openlocationcode import openlocationcode as olc
    HAS_OLC = True
except ImportError:
    HAS_OLC = False

logger = logging.getLogger(__name__)


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

# Plus Code pattern (e.g., F9C7+3HV, 8FVC9G+Q2)
# After URL decoding, + becomes space, so match both: F9C7+3HV or F9C7 3HV
PLUS_CODE_PATTERN = re.compile(r'^([23456789CFGHJMPQRVWX]{4,8})[+\s]([23456789CFGHJMPQRVWX]{2,4})\s*')


def _decode_plus_code(q_value: str) -> Optional[dict]:
    """Try to decode a Plus Code from a Google Maps ?q= value.
    Returns {lat, lng, display_name} if successful, None otherwise.
    
    Plus Codes like 'F9C7+3HV Indira Nilayam, Kondapur, Hyderabad' contain:
    - A short Plus Code (F9C7+3HV) 
    - A text address for reference location recovery
    """
    if not HAS_OLC:
        return None
    
    # Extract Plus Code from start of q_value
    # Match patterns like: F9C7+3HV or F9C7 3HV (URL-decoded)
    code_match = PLUS_CODE_PATTERN.match(q_value.strip())
    if not code_match:
        return None
    
    # Reconstruct the Plus Code with + sign
    short_code = f"{code_match.group(1)}+{code_match.group(2)}"
    remaining_text = q_value[code_match.end():].strip().strip(',')
    
    logger.info(f"Found Plus Code: {short_code}, address context: {remaining_text[:60]}")
    
    try:
        # Check if it's already a full code (10+ chars)
        if olc.isValid(short_code) and olc.isFull(short_code):
            decoded = olc.decode(short_code)
            display = _clean_maps_address(remaining_text) if remaining_text else f"Location ({decoded.latitudeCenter:.6f}, {decoded.longitudeCenter:.6f})"
            return {
                "lat": decoded.latitudeCenter,
                "lng": decoded.longitudeCenter,
                "display_name": display
            }
        
        # Short code — need a reference location from the address text
        if not remaining_text:
            return None
        
        # Get reference coordinates by geocoding the address text
        cleaned_addr = _clean_maps_address(remaining_text)
        ref_lat, ref_lng = _get_reference_coords(cleaned_addr)
        
        if ref_lat is None:
            logger.warning(f"Could not get reference coords for Plus Code recovery from: {cleaned_addr}")
            return None
        
        # Recover the full Plus Code using reference location
        full_code = olc.recoverNearest(short_code, ref_lat, ref_lng)
        logger.info(f"Recovered full Plus Code: {short_code} -> {full_code}")
        
        decoded = olc.decode(full_code)
        
        # Build a display name from the address text
        display = cleaned_addr.split(',')[0].strip() if cleaned_addr else f"Location ({decoded.latitudeCenter:.6f}, {decoded.longitudeCenter:.6f})"
        # Add area context
        parts = [p.strip() for p in cleaned_addr.split(',')]
        if len(parts) >= 2:
            display = f"{parts[0]}, {parts[-2] if len(parts) > 2 else parts[-1]}"
        
        return {
            "lat": decoded.latitudeCenter,
            "lng": decoded.longitudeCenter,
            "display_name": display
        }
    except Exception as e:
        logger.warning(f"Plus Code decoding failed for {short_code}: {e}")
        return None


def _get_reference_coords(address_text: str) -> tuple:
    """Get approximate reference coordinates by geocoding an address.
    Used for Plus Code recovery. Returns (lat, lng) or (None, None)."""
    # Try progressively simpler address queries  
    parts = [p.strip() for p in address_text.split(',') if p.strip()]
    candidates = [address_text]
    if len(parts) > 2:
        candidates.append(', '.join(parts[-3:]))
    if len(parts) > 1:
        candidates.append(', '.join(parts[-2:]))
    
    headers = {"User-Agent": "AILogisticsApp/1.0"}
    for query in candidates:
        result = _nominatim_query(query, headers)
        if result:
            return float(result["lat"]), float(result["lon"])
    
    return None, None


def _clean_maps_address(raw_address: str) -> str:
    """Clean a Google Maps address for geocoding.
    Strips Plus Codes, postal codes, and other noise that breaks Nominatim."""
    text = raw_address.strip()
    
    # Strip Plus Code prefix (e.g., "F9C7+3HV Indira Nilayam" -> "Indira Nilayam")
    text = PLUS_CODE_PATTERN.sub('', text)
    
    # Strip Indian postal codes (6 digits)
    text = re.sub(r'\b\d{6}\b', '', text)
    
    # Strip US-style zip codes
    text = re.sub(r'\b\d{5}(-\d{4})?\b', '', text)
    
    # Clean up multiple commas, trailing commas, excess whitespace
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r',\s*$', '', text)
    text = re.sub(r'^\s*,', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def _expand_shortlink(url: str) -> str:
    """Expand shortlinks like maps.app.goo.gl and extract best URL or Title"""
    try:
        with httpx.Client(follow_redirects=True, timeout=8.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) AppleWebKit/605.1.15 Chrome/91.0",
                "Accept-Language": "en-US,en;q=0.9"
            }
            response = client.get(url, headers=headers)
            
            # Collect ALL URLs in the redirect chain
            urls = [url]
            for r in response.history:
                loc = str(r.headers.get("Location", ""))
                if loc:
                    urls.append(loc)
                urls.append(str(r.url))
            urls.append(str(response.url))
            
            # Priority 1: Find @ coordinates in any URL
            for u in urls:
                at_match = MAPS_AT_PATTERN.search(u)
                if at_match:
                    return u
            
            # Priority 2: Find ?q= with content
            for u in urls:
                q_match = re.search(r'[?&](?:q|ll|query)=([^&]+)', u)
                if q_match:
                    q_val = urllib.parse.unquote_plus(q_match.group(1))
                    # If q contains coordinates, return as-is
                    if re.match(r'^-?\d+\.\d+[,\s]+-?\d+\.\d+$', q_val.strip()):
                        return u
                    
                    # Try to decode Plus Code for exact coordinates
                    plus_result = _decode_plus_code(q_val)
                    if plus_result:
                        lat, lng = plus_result["lat"], plus_result["lng"]
                        display = plus_result["display_name"]
                        logger.info(f"Plus Code decoded: ({lat}, {lng}) = {display}")
                        return f"COORDS:{lat},{lng},{display}"
                    
                    # Fallback: q contains a text address — clean it and return for geocoding
                    cleaned = _clean_maps_address(q_val)
                    if cleaned and len(cleaned) > 3:
                        logger.info(f"Short link expanded to address: {cleaned}")
                        return f"GEOCODE_TITLE:{cleaned}"
                    return u
            
            # Priority 3: Check for center= in HTML
            text = response.text
            match = re.search(r'center=(-?\d+\.\d+)[,%C2]+(-?\d+\.\d+)', text)
            if match:
                return f"https://maps.google.com/?q={match.group(1)},{match.group(2)}"
            
            # Priority 4: Extract Place name from HTML title
            title_match = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).replace("- Google Maps", "").replace("Google Maps", "").strip()
                if title:
                    return f"GEOCODE_TITLE:{title}"
                
            return urls[-1]
    except Exception as e:
        logger.warning(f"Short link expansion failed: {e}")
        return url


def _nominatim_query(query: str, headers: dict) -> dict:
    """Run a single Nominatim geocoding query. Returns the best match or None."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
    except Exception as e:
        logger.warning(f"Nominatim query failed for '{query}': {e}")
    return None


def _geocode_address(text: str, result: LocationResult) -> bool:
    """Free Text Geocoding via OpenStreetMap (Nominatim) with progressive simplification.
    Tries increasingly simpler address queries until one returns coordinates."""
    try:
        if len(text) < 3:
            return False
        
        headers = {"User-Agent": "AILogisticsApp/1.0"}
        
        # Clean the input address
        cleaned = _clean_maps_address(text)
        
        # Build progressive query candidates (most specific → least specific)
        candidates = []
        if cleaned:
            candidates.append(cleaned)
        
        # If comma-separated address, try subsets: last 4, last 3, last 2 parts
        parts = [p.strip() for p in cleaned.split(',') if p.strip()]
        if len(parts) > 3:
            candidates.append(', '.join(parts[-4:]))  # last 4 parts
        if len(parts) > 2:
            candidates.append(', '.join(parts[-3:]))  # last 3 parts
        if len(parts) > 1:
            candidates.append(', '.join(parts[-2:]))  # last 2 parts
        
        # Also try original text if different from cleaned
        if text.strip() != cleaned and text.strip() not in candidates:
            candidates.append(text.strip())
        
        # Deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c.lower() not in seen and len(c) >= 3:
                seen.add(c.lower())
                unique_candidates.append(c)
        
        # Try each candidate
        for query in unique_candidates:
            logger.info(f"Geocoding attempt: '{query}'")
            best = _nominatim_query(query, headers)
            if best:
                result.lat = float(best["lat"])
                result.lng = float(best["lon"])
                result.precision = "exact"
                
                raw_name = best.get("display_name", query)
                name_parts = raw_name.split(",")
                if len(name_parts) > 2:
                    clean_name = f"{name_parts[0].strip()}, {name_parts[1].strip()}"
                else:
                    clean_name = raw_name
                    
                result.display_name = clean_name
                logger.info(f"Geocoded '{query}' -> ({result.lat}, {result.lng}) = {clean_name}")
                return True
                
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
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
        if expanded.startswith("COORDS:"):
            # Plus Code decoded — exact coordinates available
            parts = expanded.replace("COORDS:", "").split(",", 2)
            result.lat = float(parts[0])
            result.lng = float(parts[1])
            result.precision = "exact"
            result.display_name = parts[2] if len(parts) > 2 else f"Location ({result.lat}, {result.lng})"
            logger.info(f"Shortlink resolved via Plus Code: ({result.lat}, {result.lng}) = {result.display_name}")
            return result
        elif expanded.startswith("GEOCODE_TITLE:"):
            extracted_title = expanded.replace("GEOCODE_TITLE:", "")
            # Directly geocode the extracted address — skip known-location partial matching
            # which would incorrectly match area names (e.g., "kondapur") as low precision
            logger.info(f"Geocoding extracted address from shortlink: {extracted_title}")
            if _geocode_address(extracted_title, result):
                return result
            # If Nominatim fails, still set the text for downstream processing
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
