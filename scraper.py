#!/usr/bin/env python3

import os
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

# Constants
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.0
DEFAULT_TIMEOUT = 10
JSON_CONTENT_PREVIEW_LENGTH = 1000

# Optional: use requests if available, otherwise fallback to urllib
try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request  # type: ignore
    _HAS_REQUESTS = False

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.lazada.sg/pokemon-store-online-singapore/",
}

def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def fetch_json(url: str,
               headers: Optional[Dict[str, str]] = None,
               retries: int = DEFAULT_RETRIES,
               backoff: float = DEFAULT_BACKOFF,
               timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Fetch JSON from `url` with retries. Returns parsed JSON dict or None.
    Uses requests if available, otherwise urllib.
    """
    headers = headers or DEFAULT_HEADERS
    attempt = 0
    while attempt < retries:
        try:
            if _HAS_REQUESTS:
                resp = requests.get(url, headers=headers, timeout=timeout)
                text = resp.text
                status = resp.status_code
                if status != 200:
                    print(f"[{get_timestamp()}] HTTP {status} from {url}")
                    raise RuntimeError(f"HTTP {status}")
            else:
                req = _urllib_request.Request(url, headers=headers)
                with _urllib_request.urlopen(req, timeout=timeout) as r:
                    text = r.read().decode("utf-8")
            # Try parse JSON
            try:
                data = json.loads(text)
                return data
            except json.JSONDecodeError:
                # Lazada sometimes returns HTML containing a JSON blob or anti-bot page
                print(f"[{get_timestamp()}] Failed to parse JSON on attempt {attempt+1}.")
                # Print the response content for debugging (truncate if too long)
                response_preview = (text[:JSON_CONTENT_PREVIEW_LENGTH] + "..." 
                                 if len(text) > JSON_CONTENT_PREVIEW_LENGTH else text)
                print(f"[{get_timestamp()}] Response content: {response_preview}")
                # Attempt to locate JSON substring as a last resort
                json_start_pattern = '{"mods"'
                start = text.find(json_start_pattern)
                if start != -1:
                    try:
                        data = json.loads(text[start:])
                        return data
                    except json.JSONDecodeError:
                        pass
                raise
        except Exception as e:
            attempt += 1
            wait = backoff * (2 ** (attempt - 1))
            print(f"[{get_timestamp()}] Fetch attempt {attempt} failed: {e}. Retrying in {wait:.1f}s...")
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
    You can adjust logic (e.g., price not None, or stock > 0).
    """
    available = [p for p in products if p.get("inStock") is True]
    return available

def main():
    print(f"[{get_timestamp()}] Scraper starting (simplified JSON fetch)...")
    
    # Get URLs from environment variables
    url = os.environ.get("SCRAPING_URL")
    intl_url = os.environ.get("SCRAPING_URL_INTL_ETB")
    
    all_products = []
    
    # Scrape from primary URL
    if url:
        print(f"[{get_timestamp()}] Fetching from primary URL: {url}")
        payload = fetch_json(url)
        if payload is not None:
            products = extract_products_from_payload(payload)
            if products:
                # Mark products with source
                for product in products:
                    product["source"] = "primary"
                all_products.extend(products)
                print(f"[{get_timestamp()}] Found {len(products)} products from primary source")
            else:
                print(f"[{get_timestamp()}] No products found in primary payload.")
                # Save the raw payload for inspection
                try:
                    debug_fn = f"raw_payload_primary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(debug_fn, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                    print(f"[{get_timestamp()}] Primary raw payload saved to {debug_fn} for debugging.")
                except Exception as e:
                    print(f"[{get_timestamp()}] Failed to save primary raw payload: {e}")
        else:
            print(f"[{get_timestamp()}] Failed to fetch or parse primary JSON payload.")
    else:
        print(f"[{get_timestamp()}] SCRAPING_URL not set, skipping primary source")
    
    # Scrape from international ETB URL
    if intl_url:
        print(f"[{get_timestamp()}] Fetching from INTL ETB URL: {intl_url}")
        intl_payload = fetch_json(intl_url)
        if intl_payload is not None:
            intl_products = extract_products_from_payload(intl_payload)
            if intl_products:
                # Mark products with source
                for product in intl_products:
                    product["source"] = "intl_etb"
                all_products.extend(intl_products)
                print(f"[{get_timestamp()}] Found {len(intl_products)} products from INTL ETB source")
            else:
                print(f"[{get_timestamp()}] No products found in INTL ETB payload.")
                # Save the raw payload for inspection
                try:
                    debug_fn = f"raw_payload_intl_etb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(debug_fn, "w", encoding="utf-8") as f:
                        json.dump(intl_payload, f, indent=2, ensure_ascii=False)
                    print(f"[{get_timestamp()}] INTL ETB raw payload saved to {debug_fn} for debugging.")
                except Exception as e:
                    print(f"[{get_timestamp()}] Failed to save INTL ETB raw payload: {e}")
        else:
            print(f"[{get_timestamp()}] Failed to fetch or parse INTL ETB JSON payload.")
    else:
        print(f"[{get_timestamp()}] SCRAPING_URL_INTL_ETB not set, skipping INTL ETB source")
    
    # Check if we have any products at all
    if not all_products:
        print(f"[{get_timestamp()}] No products found from any source. Exiting.")
        return

    available_products = filter_available_products(all_products)

    # Log total and available products count before notifications
    print(f"[{get_timestamp()}] Total products found: {len(all_products)}")
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
