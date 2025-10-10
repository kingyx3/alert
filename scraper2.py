#!/usr/bin/env python3

import os
import json
from datetime import datetime

# Import shared components
from scraper_common import (
    get_timestamp,
    fetch_json, 
    extract_products_from_payload,
    filter_available_products
)

# Custom headers for scraper2.py based on Lazada requirements (excluding cookies and session-specific data)
SCRAPER2_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i",
    "Referer": "https://www.lazada.sg/",
    "Sec-Ch-Ua": '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
}

def main():
    print(f"[{get_timestamp()}] Scraper2 starting (simplified JSON fetch)...")
    url = os.environ.get("SCRAPING_URL_2")
    print(f"[{get_timestamp()}] Fetching: {url}")

     payload, raw_text = fetch_json(url, headers=SCRAPER2_HEADERS)
    if payload is None:
        print(f"[{get_timestamp()}] Failed to fetch or parse JSON payload. Exiting.")
        return

    products = extract_products_from_payload(payload)
    if not products:
        print(f"[{get_timestamp()}] No products found in payload. The site may have returned an anti-bot page or different format.")

        # Log the first 10000 characters of the page
        if raw_text:
            page_preview = raw_text[:10000]
            print(f"[{get_timestamp()}] First 10000 characters of page content:")
            print(page_preview)

        print(f"[{get_timestamp()}] No products found in payload. The site may have returned an anti-bot page or different format.")
        # Save the raw payload for inspection
        try:
            debug_fn = f"raw_payload_scraper2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_fn, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] Raw payload saved to {debug_fn} for debugging.")
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to save raw payload: {e}")
        return

    # Log all products after sorting (even if they aren't available)
    from scraper_common import log_all_products_sorted
    log_all_products_sorted(products)

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
        filename = f"available_products_scraper2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] Available products saved to {filename}")
        except Exception as e:
            print(f"[{get_timestamp()}] Error saving results: {str(e)}")
    else:
        print(f"[{get_timestamp()}] No available products found.")

    print(f"[{get_timestamp()}] Scraper2 completed.")

if __name__ == "__main__":
    main()