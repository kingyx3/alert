#!/usr/bin/env python3
"""
International scraper module for ETB sites using selenium-based scraping.

This module uses the SCRAPING_URL_INTL_ETB environment variable and implements
selenium-based scraping similar to scraper_old.py for international e-commerce sites.
"""

import os
import json
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

# Add old directory to path to import scraper components
sys.path.append(os.path.join(os.path.dirname(__file__), 'old'))

# Import the refactored components from old directory
from scraper_components.core.browser_scraper import BrowserScraper
from scraper_components.utils.helpers import get_timestamp

# Import all constants for compatibility
from scraper_components.config.constants import (
    DEFAULT_WINDOW_SIZE, SYSTEM_CHROMEDRIVER_PATH, PRODUCT_SELECTORS,
    PRICE_SELECTORS, TITLE_SELECTORS, PRICE_EXTRACT_SELECTORS,
    QUANTITY_SELECTORS, BUY_INDICATORS, CRITICAL_ERROR_INDICATORS,
    PRODUCT_PAGE_INDICATORS
)


class InternationalBrowserScraper(BrowserScraper):
    """International browser scraper that uses SCRAPING_URL_INTL_ETB."""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use SCRAPING_URL_INTL_ETB environment variable instead of SCRAPING_URL
        intl_url = base_url or os.getenv('SCRAPING_URL_INTL_ETB')
        super().__init__(intl_url)
        
        if not self.base_url:
            print(f"[{get_timestamp()}] Warning: SCRAPING_URL_INTL_ETB environment variable not set")


def main():
    """Main entry point for international scraper."""
    print(f"[{get_timestamp()}] International Scraper starting...")
    
    # Check if SCRAPING_URL_INTL_ETB is set
    intl_url = os.getenv('SCRAPING_URL_INTL_ETB')
    if not intl_url:
        print(f"[{get_timestamp()}] Error: SCRAPING_URL_INTL_ETB environment variable not set")
        print(f"[{get_timestamp()}] Please set the SCRAPING_URL_INTL_ETB environment variable and try again")
        return
    
    print(f"[{get_timestamp()}] Using international URL: {intl_url}")
    
    # Initialize international browser scraper
    browser_scraper = InternationalBrowserScraper()
    available_products = browser_scraper.scrape_products()

    # Try to send notifications if notification_service module exists
    try:
        from notification_service import create_notification_service
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
        filename = f"available_products_intl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] Available products saved to {filename}")
        except Exception as e:
            print(f"[{get_timestamp()}] Error saving results: {str(e)}")
    else:
        print(f"[{get_timestamp()}] No available products found.")

    print(f"[{get_timestamp()}] International scraper completed.")


if __name__ == "__main__":
    main()