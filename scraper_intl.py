#!/usr/bin/env python3
"""
Enhanced International Scraper with Anti-Bot Detection Measures

This scraper includes comprehensive anti-bot detection workarounds:
- Rotates between 5 realistic user agents
- Maintains session state with cookies
- Adds human-like delays and randomized backoff
- Simulates browser navigation patterns (referrer -> target)
- Detects and adapts to bot blocking responses
- Uses modern browser headers (sec-ch-ua, Sec-Fetch-*, etc.)

The key improvement addresses the issue where clicking hyperlinks triggers
bot detection, but pasting URLs directly in browsers works fine.
"""

import os
import json
import time
import random
from datetime import datetime
from typing import List, Optional, Dict, Any

# Constants
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.0
DEFAULT_TIMEOUT = 10
JSON_CONTENT_PREVIEW_LENGTH = 1000
POKEMON_CENTER_REFERRER_URL = "https://www.pokemoncenter.com/category/tcg-cards?category=tcg-cards"

# Optional: use requests if available, otherwise fallback to urllib
try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request  # type: ignore
    import urllib.parse as _urllib_parse  # type: ignore
    _HAS_REQUESTS = False

# Rotate between multiple realistic user agents (updated to match Pokemon Center compatible versions)
USER_AGENTS = [
    # Exact match from Pokemon Center browser headers
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
    # Additional compatible user agents for variety
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15"
]

def get_realistic_headers(referer: Optional[str] = None) -> Dict[str, str]:
    """Generate realistic browser headers with random user agent, optimized for Pokemon Center API."""
    user_agent = random.choice(USER_AGENTS)
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    if referer:
        headers["Referer"] = referer
        # When coming from a referrer, adjust Sec-Fetch-Site
        if referer.startswith("http"):
            headers["Sec-Fetch-Site"] = "cross-site"
    
    # Add browser-specific headers based on user agent - using Pokemon Center compatible versions
    if "Chrome" in user_agent and "Edg" in user_agent:
        # Microsoft Edge - match the provided browser headers
        headers.update({
            "sec-ch-ua": '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-full-version-list": '"Microsoft Edge";v="141.0.3537.57", "Not?A_Brand";v="8.0.0.0", "Chromium";v="141.0.7390.55"',
            "sec-ch-ua-model": '""',
            "sec-ch-device-memory": "8"
        })
    elif "Chrome" in user_agent:
        # Google Chrome - similar headers but Chrome branded
        headers.update({
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"' if "Windows" in user_agent else '"macOS"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-model": '""',
            "sec-ch-device-memory": "8"
        })
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        # Safari doesn't use sec-ch-ua headers
        pass
    elif "Firefox" in user_agent:
        # Firefox doesn't use sec-ch-ua headers
        pass
    
    # Add Pokemon Center specific header
    headers["x-store-scope"] = "pokemon"
    
    return headers

DEFAULT_HEADERS = get_realistic_headers("https://www.google.com/")

def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Global session for maintaining cookies and state
_SESSION = None

def get_session():
    """Get or create a requests session with browser-like configuration."""
    global _SESSION
    if _SESSION is None and _HAS_REQUESTS:
        _SESSION = requests.Session()
        # Configure session with browser-like settings
        _SESSION.headers.update(get_realistic_headers())
        # Enable cookies
        _SESSION.cookies.clear()
    return _SESSION

def human_delay(min_delay: float = 0.5, max_delay: float = 2.0):
    """Add random delay to mimic human browsing behavior."""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def fetch_json(url: str,
               headers: Optional[Dict[str, str]] = None,
               retries: int = DEFAULT_RETRIES,
               backoff: float = DEFAULT_BACKOFF,
               timeout: int = DEFAULT_TIMEOUT,
               use_session: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch JSON from `url` with retries. Returns parsed JSON dict or None.
    Uses requests session if available for better bot detection avoidance, otherwise urllib.
    """
    if headers is None:
        headers = get_realistic_headers()
    
    attempt = 0
    while attempt < retries:
        try:
            # Add human-like delay before request
            if attempt > 0:
                human_delay(1.0, 3.0)  # Longer delay on retries
            else:
                human_delay(0.2, 0.8)  # Short delay on first attempt
            
            if _HAS_REQUESTS:
                session = get_session() if use_session else None
                
                if session:
                    # Update session headers for this request
                    session.headers.update(headers)
                    resp = session.get(url, timeout=timeout)
                else:
                    resp = requests.get(url, headers=headers, timeout=timeout)
                
                text = resp.text
                status = resp.status_code
                
                # Check for common bot detection responses
                if status == 403:
                    print(f"[{get_timestamp()}] Access forbidden (403) - possible bot detection from {url}")
                elif status == 429:
                    print(f"[{get_timestamp()}] Rate limited (429) - backing off from {url}")
                    human_delay(5.0, 10.0)  # Longer delay for rate limiting
                elif status != 200:
                    print(f"[{get_timestamp()}] HTTP {status} from {url}")
                    
                if status not in [200, 403, 429]:
                    raise RuntimeError(f"HTTP {status}")
                    
            else:
                req = _urllib_request.Request(url, headers=headers)
                with _urllib_request.urlopen(req, timeout=timeout) as r:
                    text = r.read().decode("utf-8")
                    status = 200
            # Check for bot detection in response
            if status == 403 or "captcha" in text.lower() or "blocked" in text.lower():
                print(f"[{get_timestamp()}] Possible bot detection on attempt {attempt+1}. Response indicates blocking.")
                # Try with different headers on next attempt
                headers = get_realistic_headers("https://www.google.com/")
                attempt += 1
                if attempt < retries:
                    wait = backoff * (2 ** (attempt - 1)) + random.uniform(1, 3)
                    print(f"[{get_timestamp()}] Bot detection suspected. Retrying with new headers in {wait:.1f}s...")
                    time.sleep(wait)
                continue
            
            # Try parse JSON
            try:
                data = json.loads(text)
                print(f"[{get_timestamp()}] Successfully fetched and parsed JSON from {url}")
                return data
            except json.JSONDecodeError:
                # Lazada sometimes returns HTML containing a JSON blob or anti-bot page
                print(f"[{get_timestamp()}] Failed to parse JSON on attempt {attempt+1}.")
                # Print the response content for debugging (truncate if too long)
                response_preview = (text[:JSON_CONTENT_PREVIEW_LENGTH] + "..." 
                                 if len(text) > JSON_CONTENT_PREVIEW_LENGTH else text)
                print(f"[{get_timestamp()}] Response content: {response_preview}")
                
                # Check if this looks like an anti-bot page
                if any(keyword in text.lower() for keyword in ['robot', 'bot', 'captcha', 'security check', 'verify', 'cloudflare']):
                    print(f"[{get_timestamp()}] Response appears to be an anti-bot page.")
                    # Try with different headers on next attempt
                    headers = get_realistic_headers("https://www.google.com/")
                    
                # Attempt to locate JSON substring as a last resort
                json_start_pattern = '{"mods"'
                start = text.find(json_start_pattern)
                if start != -1:
                    try:
                        data = json.loads(text[start:])
                        print(f"[{get_timestamp()}] Found and parsed JSON substring from response")
                        return data
                    except json.JSONDecodeError:
                        pass
                raise
        except Exception as e:
            attempt += 1
            wait = backoff * (2 ** (attempt - 1)) + random.uniform(0.5, 2.0)  # Add randomness to backoff
            print(f"[{get_timestamp()}] Fetch attempt {attempt} failed: {e}. Retrying in {wait:.1f}s...")
            
            # Use fresh headers for next attempt
            if attempt < retries:
                headers = get_realistic_headers("https://www.google.com/")
                
            time.sleep(wait)
    print(f"[{get_timestamp()}] All {retries} fetch attempts failed for {url}")
    return None

def extract_products_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given parsed JSON payload (expected to contain mods.listItems),
    returns a list of product dicts with normalized fields.
    """
    products: List[Dict[str, Any]] = []
    mods = payload.get("mods") or payload.get("modsData") or {}
    list_items = mods.get("listItems") or []
    
    if not isinstance(list_items, list):
        return products

    for item in list_items:
        try:
            # Normalize price to float when possible
            price_raw = item.get("price")
            price = None
            if price_raw is not None and price_raw != "":
                try:
                    price = float(price_raw)
                except (ValueError, TypeError):
                    price = None

            product = {
                "name": item.get("name") or item.get("title") or "",
                "price": price,
                "priceShow": item.get("priceShow") or item.get("originalPriceShow") or "",
                "inStock": bool(item.get("inStock")),
                "sold": item.get("itemSoldCntShow") or item.get("itemSoldCnt") or "",
                "rating": item.get("ratingScore"),
                "reviews": item.get("review") or item.get("reviewCount"),
                "url": ("https:" + item["itemUrl"]) if item.get("itemUrl") else None,
                "image": item.get("image"),
                "skuId": item.get("skuId"),
                "sku": item.get("sku"),
                "sellerName": item.get("sellerName"),
                "sellerId": item.get("sellerId"),
                "raw": item,
            }
            products.append(product)
        except Exception as e:
            print(f"[{get_timestamp()}] Skipping an item due to parse error: {e}")

    return products

def filter_available_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns subset of products that are considered 'available'.
    Here we treat products with inStock == True as available.
    
    PRODUCT NAME FILTER:
    By default, only products containing "TCG" or "Trading" in their name are considered.
    This can be customized via the PRODUCT_NAME_FILTERS environment variable:
    - Set to comma-separated keywords: PRODUCT_NAME_FILTERS="TCG,Trading,Pokemon"
    - Set to empty string to disable filtering: PRODUCT_NAME_FILTERS=""
    - Default: "TCG,Trading" if not set
    
    You can adjust logic (e.g., price not None, or stock > 0).
    """
    def contains_filter_keywords(product_name: str) -> bool:
        """Check if product name contains any of the configured filter keywords (case-insensitive)."""
        if not product_name:
            return False
        
        # Get filter keywords from environment variable, default to "TCG,Trading"
        filter_keywords_str = os.environ.get("PRODUCT_NAME_FILTERS", "TCG,Trading")
        
        # If empty string, disable filtering (return True for all products)
        if not filter_keywords_str.strip():
            return True
        
        # Parse comma-separated keywords and check if any match
        keywords = [kw.strip().lower() for kw in filter_keywords_str.split(",") if kw.strip()]
        if not keywords:
            return True  # If no valid keywords, don't filter
        
        name_lower = product_name.lower()
        return any(keyword in name_lower for keyword in keywords)
    
    available = [
        p for p in products 
        if p.get("inStock") is True and contains_filter_keywords(p.get("name", ""))
    ]
    return available

def simulate_browser_navigation(target_url: str) -> Optional[Dict[str, Any]]:
    """
    Simulate browser navigation by first visiting Pokemon Center TCG category page, then the target.
    This helps avoid bot detection when clicking links vs direct URL access.
    """
    if not target_url:
        return None
        
    print(f"[{get_timestamp()}] Simulating browser navigation to avoid bot detection...")
    
    # First, simulate visiting the Pokemon Center TCG cards category page
    print(f"[{get_timestamp()}] Simulating visit from Pokemon Center referrer: {POKEMON_CENTER_REFERRER_URL}")
    
    # Add a realistic delay as if browsing from the category page
    human_delay(1.0, 3.0)
    
    # Now fetch the target URL with the Pokemon Center category page as referrer
    headers = get_realistic_headers(POKEMON_CENTER_REFERRER_URL)
    return fetch_json(target_url, headers=headers, use_session=True)

def main():
    print(f"[{get_timestamp()}] Scraper starting (simplified JSON fetch)...")
    url = os.environ.get("SCRAPING_URL_INTL")
    print(f"[{get_timestamp()}] Target URL: {url}")
    
    # Use enhanced navigation simulation to avoid bot detection
    payload = simulate_browser_navigation(url)
    if payload is None:
        print(f"[{get_timestamp()}] Failed to fetch or parse JSON payload. Exiting.")
        return

    products = extract_products_from_payload(payload)
    if not products:
        print(f"[{get_timestamp()}] No products found in payload. The site may have returned an anti-bot page or different format.")
        # Save the raw payload for inspection
        try:
            debug_fn = f"raw_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_fn, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] Raw payload saved to {debug_fn} for debugging.")
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to save raw payload: {e}")
        return

    available_products = filter_available_products(products)

    # Log total and available products count before notifications
    print(f"[{get_timestamp()}] Total products found: {len(products)}")
    print(f"[{get_timestamp()}] Available products: {len(available_products)}")

    # Try to send notifications if notification_service module exists
    try:
        from notification_service import create_notification_service  # type: ignore
        notification_service = create_notification_service()
        if available_products:
            print(f"[{get_timestamp()}] Found {len(available_products)} available products")
            success = notification_service.notify_products(available_products)
            if success:
                print(f"[{get_timestamp()}] Product notifications sent successfully")
            else:
                print(f"[{get_timestamp()}] Failed to send product notifications")
        else:
            print(f"[{get_timestamp()}] No available products found - no notifications sent")
    except ImportError:
        print(f"[{get_timestamp()}] Notification service not available - running without notifications")
    except Exception as e:
        print(f"[{get_timestamp()}] Error in notification service: {str(e)}")

    # Save results to JSON if any available products found
    if available_products:
        print(f"[{get_timestamp()}] Available products found: {len(available_products)}")
        filename = f"available_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] Available products saved to {filename}")
        except Exception as e:
            print(f"[{get_timestamp()}] Error saving results: {str(e)}")
    else:
        print(f"[{get_timestamp()}] No available products found.")

    print(f"[{get_timestamp()}] Scraper completed.")

if __name__ == "__main__":
    main()
