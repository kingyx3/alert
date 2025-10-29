#!/usr/bin/env python3
"""
Common scraper components shared between multiple scraper modules.
Contains reusable functions for JSON fetching, data extraction, and utility operations.
"""

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
    "Referer": "https://www.lazada.sg/",
}

# Cache for parsed filter keywords to avoid repeated parsing
_FILTER_KEYWORDS_CACHE: Optional[tuple[str, List[str]]] = None

def get_filter_keywords() -> List[str]:
    """
    Get the list of filter keywords from PRODUCT_NAME_FILTERS environment variable.
    Results are cached to avoid repeated parsing.
    
    Returns:
        List of lowercase filter keywords. Empty list means no filtering.
    """
    global _FILTER_KEYWORDS_CACHE
    
    # Get current environment variable value
    filter_keywords_str = os.environ.get("PRODUCT_NAME_FILTERS", "TCG,Trading")
    
    # Check if we have a cached value for this exact string
    if _FILTER_KEYWORDS_CACHE is not None and _FILTER_KEYWORDS_CACHE[0] == filter_keywords_str:
        return _FILTER_KEYWORDS_CACHE[1]
    
    # Parse and cache the keywords
    if not filter_keywords_str.strip():
        keywords = []  # Empty list means no filtering (return all in-stock products)
    else:
        keywords = [kw.strip().lower() for kw in filter_keywords_str.split(",") if kw.strip()]
    
    _FILTER_KEYWORDS_CACHE = (filter_keywords_str, keywords)
    return keywords

def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def fetch_json(url: str,
               headers: Optional[Dict[str, str]] = None,
               retries: int = DEFAULT_RETRIES,
               backoff: float = DEFAULT_BACKOFF,
               timeout: int = DEFAULT_TIMEOUT) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch JSON from `url` with retries. Returns tuple of (parsed JSON dict or None, raw text or None).
    Uses requests if available, otherwise urllib.
    Raises RuntimeError if all attempts fail.
    """
    headers = headers or DEFAULT_HEADERS
    attempt = 0
    last_exception = None

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
                return data, text
            except json.JSONDecodeError:
                print(f"[{get_timestamp()}] Failed to parse JSON on attempt {attempt+1}.")
                response_preview = (text[:JSON_CONTENT_PREVIEW_LENGTH] + "..." 
                                    if len(text) > JSON_CONTENT_PREVIEW_LENGTH else text)
                print(f"[{get_timestamp()}] Response content: {response_preview}")

                # Attempt to locate JSON substring as a last resort
                json_start_pattern = '{"mods"'
                start = text.find(json_start_pattern)
                if start != -1:
                    try:
                        data = json.loads(text[start:])
                        return data, text
                    except json.JSONDecodeError:
                        pass
                raise

        except Exception as e:
            last_exception = e
            attempt += 1
            wait = backoff * (2 ** (attempt - 1))
            print(f"[{get_timestamp()}] Fetch attempt {attempt} failed: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)

    # After all retries fail
    error_msg = f"[{get_timestamp()}] All {retries} fetch attempts failed for {url}"
    print(error_msg)

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
        
        # Get filter keywords using cached utility function
        keywords = get_filter_keywords()
        
        # If empty list, no filtering (return True for all products)
        if not keywords:
            return True
        
        name_lower = product_name.lower()
        return any(keyword in name_lower for keyword in keywords)
    
    available = [
        p for p in products 
        if p.get("inStock") is True and contains_filter_keywords(p.get("name", ""))
    ]
    return available

def log_all_products_sorted(products: List[Dict[str, Any]]) -> None:
    """
    Log all products (available and unavailable) sorted alphabetically by name.
    This provides a comprehensive view of all scraped products.
    """
    if not products:
        print(f"[{get_timestamp()}] No products to display.")
        return
    
    # Sort products alphabetically by name (same as notification service)
    sorted_products = sorted(products, key=lambda x: x.get('name', '').lower())
    
    print(f"[{get_timestamp()}] All products found (sorted alphabetically):")
    print(f"[{get_timestamp()}] {'='*80}")
    
    for idx, product in enumerate(sorted_products, 1):
        name = product.get('name', 'Unknown Product')
        price_show = product.get('priceShow', 'N/A')
        if not price_show and 'price' in product and product['price'] is not None:
            price_show = f"${product['price']:.2f}"
        elif not price_show:
            price_show = 'N/A'
        
        in_stock = product.get('inStock', False)
        stock_status = "✅ Available" if in_stock else "❌ Not Available"
        
        sold = product.get('sold', '')
        sold_text = f' - {sold}' if sold else ''
        
        url = product.get('url', 'No URL')
        
        print(f"[{get_timestamp()}] {idx:3d}. {name} ({price_show}){sold_text}")
        print(f"[{get_timestamp()}]      Status: {stock_status}")
        print(f"[{get_timestamp()}]      URL: {url}")
        
        # Add a separator line for readability except for the last item
        if idx < len(sorted_products):
            print(f"[{get_timestamp()}] {'-'*80}")
    
    print(f"[{get_timestamp()}] {'='*80}")
    
    # Summary statistics
    available_count = sum(1 for p in products if p.get('inStock', False))
    unavailable_count = len(products) - available_count
    print(f"[{get_timestamp()}] Total products: {len(products)} (Available: {available_count}, Unavailable: {unavailable_count})")