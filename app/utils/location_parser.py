import re
import httpx
from typing import Optional

def extract_location(message_text: str, form_data: dict = None) -> dict:
    """
    Extracts location from a WhatsApp message or Twilio payload.
    Returns dict with lat, lng, precision.
    """
    if form_data is None:
        form_data = {}
        
    result = {
        "lat": None,
        "lng": None,
        "precision": "low"
    }
    
    # STEP 1 - HANDLE WHATSAPP LOCATION (HIGHEST PRIORITY)
    latitude = form_data.get("Latitude")
    longitude = form_data.get("Longitude")
    
    if latitude and longitude:
        try:
            result["lat"] = float(latitude)
            result["lng"] = float(longitude)
            result["precision"] = "exact"
            return result
        except ValueError:
            pass

    text = message_text.strip()
    if not text:
        return result
        
    # STEP 2 - DETECT GOOGLE SHORT LINK
    if "maps.app.goo.gl" in text:
        # Extract the URL from text
        url_match = re.search(r'(https?://maps\.app\.goo\.gl/[^\s]+)', text)
        if url_match:
            try:
                # Use httpx with a 5 second timeout to follow redirects
                with httpx.Client(follow_redirects=True, timeout=5.0) as client:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response = client.get(url_match.group(1), headers=headers)
                    # The expanded URL is captured
                    text = str(response.url)
            except Exception:
                # Request failure gracefully handled
                pass

    # STEP 3 - PARSE EXPANDED URL
    # 1. r"q=([0-9.-]+),([0-9.-]+)"
    match1 = re.search(r'q=([-0-9.]+),([-0-9.]+)', text)
    if match1:
        result["lat"] = float(match1.group(1))
        result["lng"] = float(match1.group(2))
        result["precision"] = "exact"
        return result
        
    # 2. r"@([0-9.-]+),([0-9.-]+)"
    match2 = re.search(r'@([-0-9.]+),([-0-9.]+)', text)
    if match2:
        result["lat"] = float(match2.group(1))
        result["lng"] = float(match2.group(2))
        result["precision"] = "exact"
        return result
        
    # 3. r"/([-0-9.]+),([-0-9.]+)"
    match3 = re.search(r'/([-0-9.]+),([-0-9.]+)', text)
    if match3:
        result["lat"] = float(match3.group(1))
        result["lng"] = float(match3.group(2))
        result["precision"] = "exact"
        return result

    # STEP 4 - HANDLE RAW COORDINATES
    # "17.2403,78.4294"
    match4 = re.search(r'([-0-9.]+),\s*([-0-9.]+)', text)
    if match4:
        result["lat"] = float(match4.group(1))
        result["lng"] = float(match4.group(2))
        result["precision"] = "exact"
        return result
        
    # STEP 5 - FALLBACK
    return result

# --- TEST CASES ---
if __name__ == "__main__":
    def run_tests():
        print("Test 1: maps.app.goo.gl link")
        # Note: requires internet to expand properly. Adjust the URL string for live testing.
        res1 = extract_location("https://maps.app.goo.gl/dummy")
        print(res1)
        
        print("\nTest 2: google.com/maps?q=...")
        res2 = extract_location("https://google.com/maps?q=17.4399,78.3489")
        print(res2)
        
        print("\nTest 3: @lat,lng URL")
        res3 = extract_location("https://www.google.com/maps/place/Foo/@17.4399,78.3489,15z")
        print(res3)
        
        print("\nTest 4: Raw coordinates")
        res4 = extract_location("My pickup is 17.2403,78.4294")
        print(res4)
        
        print("\nTest 5: Low precision string")
        res5 = extract_location("Kondapur")
        print(res5)
        
        print("\nTest 6: Twilio WhatsApp payload")
        res6 = extract_location("", {"Latitude": "17.2403", "Longitude": "78.4294"})
        print(res6)

    run_tests()
