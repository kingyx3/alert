#!/usr/bin/env python3
"""
Refactored scraper module (simplified JSON fetch).

This version fetches the Lazada shop AJAX JSON directly (no browser automation)
and extracts product information from mods.listItems. Keeps the same
external behaviour (notification service attempt, saving available products).
"""

import os
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

# Inline helper functions (replacing scraper_components imports)
def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
    # Keep referer as Lazada shop root if useful
    "Referer": "https://www.lazada.sg/pokemon-store-online-singapore/",
}

# Default Lazada AJAX URL (use the one you provided)
DEFAULT_SHOP_AJAX_URL = (
    "https://www.lazada.sg/pokemon-store-online-singapore/"
    "?ajax=true&from=wangpu&hideSectionHeader=true&isFirstRequest=true"
    "&page=1&q=All-Products&sc=KVUG&search_scenario=store&service=store_sections"
    "&shopId=2056827&shop_category_ids=762252&spm=a2o42.10453684.0.0.2db85edfif66F6&src=store_sections"
)

def _now() -> str:
    """Backward compatibility function."""
    return get_timestamp()

def _safe_get_attr(elem: Dict[str, Any], attr: str) -> Optional[Any]:
    """Simple safe getter for dictionaries."""
    return elem.get(attr)

def fetch_json(url: str,
               headers: Optional[Dict[str, str]] = None,
               retries: int = 3,
               backoff: float = 1.0,
               timeout: int = 10) -> Optional[Dict[str, Any]]:
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
                    print(f"[{_now()}] HTTP {status} from {url}")
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
                print(f"[{_now()}] Failed to parse JSON on attempt {attempt+1}.")
                # Print the response content for debugging (truncate if too long)
                response_preview = text[:1000] + "..." if len(text) > 1000 else text
                print(f"[{_now()}] Response content: {response_preview}")
                # Attempt to locate JSON substring as a last resort
                start = text.find('{"mods"')
                if start != -1:
                    try:
                        data = json.loads(text[start:])
                        return data
                    except Exception:
                        pass
                raise
        except Exception as e:
            attempt += 1
            wait = backoff * (2 ** (attempt - 1))
            print(f"[{_now()}] Fetch attempt {attempt} failed: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)
    print(f"[{_now()}] All {retries} fetch attempts failed for {url}")
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
        # Sometimes Lazada uses another key; try to find list-like structures
        list_items = []

    for item in list_items:
        try:
            name = item.get("name") or item.get("title") or ""
            price_raw = item.get("price")  # often string or numeric
            # normalize price to float when possible
            price = None
            try:
                if price_raw is not None and price_raw != "":
                    price = float(price_raw)
            except Exception:
                price = None

            product = {
                "name": name,
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
                "raw": item,  # keep raw item for debugging if needed
            }
            products.append(product)
        except Exception as e:
            print(f"[{_now()}] Skipping an item due to parse error: {e}")

    return products

def filter_available_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns subset of products that are considered 'available'.
    Here we treat products with inStock == True as available.
    You can adjust logic (e.g., price not None, or stock > 0).
    """
    available = [p for p in products if p.get("inStock") is True]
    return available

def main(shop_ajax_url: Optional[str] = None):
    print(f"[{_now()}] Scraper starting (simplified JSON fetch)...")
    url = shop_ajax_url or os.environ.get("SCRAPING_URL") or DEFAULT_SHOP_AJAX_URL
    print(f"[{_now()}] Fetching: {url}")

    payload = fetch_json(url)
    if payload is None:
        print(f"[{_now()}] Failed to fetch or parse JSON payload. Exiting.")
        return

    products = extract_products_from_payload(payload)
    if not products:
        print(f"[{_now()}] No products found in payload. The site may have returned an anti-bot page or different format.")
        # Save the raw payload for inspection
        try:
            debug_fn = f"raw_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_fn, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"[{_now()}] Raw payload saved to {debug_fn} for debugging.")
        except Exception as e:
            print(f"[{_now()}] Failed to save raw payload: {e}")
        return

    available_products = filter_available_products(products)

    # Log total and available products count before notifications
    print(f"[{_now()}] Total products found: {len(products)}")
    print(f"[{_now()}] Available products: {len(available_products)}")

    # Try to send notifications if notification_service module exists
    try:
        from notification_service import create_notification_service  # type: ignore
        notification_service = create_notification_service()
        if available_products:
            print(f"[{_now()}] Found {len(available_products)} available products")
            success = notification_service.notify_products(available_products)
            if success:
                print(f"[{_now()}] Product notifications sent successfully")
            else:
                print(f"[{_now()}] Failed to send product notifications")
        else:
            print(f"[{_now()}] No available products found - no notifications sent")
    except ImportError:
        print(f"[{_now()}] Notification service not available - running without notifications")
    except Exception as e:
        print(f"[{_now()}] Error in notification service: {str(e)}")

    # Save results to JSON if any available products found
    if available_products:
        print('Available products:', len(available_products))
        filename = f"available_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{_now()}] Available products saved to {filename}")
        except Exception as e:
            print(f"[{_now()}] Error saving results: {str(e)}")
    else:
        print(f"[{_now()}] No available products found.")

    print(f"[{_now()}] Scraper completed.")

if __name__ == "__main__":
    main()
