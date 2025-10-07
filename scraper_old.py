#!/usr/bin/env python3
"""
Refactored scraper module providing backward compatibility.

This module maintains the original interface while using the new modular components.
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

# Import the refactored components
from scraper_components.core.browser_scraper import BrowserScraper
from scraper_components.utils.helpers import get_timestamp

# Import all constants for backward compatibility
from scraper_components.config.constants import (
    DEFAULT_WINDOW_SIZE, SYSTEM_CHROMEDRIVER_PATH, PRODUCT_SELECTORS,
    PRICE_SELECTORS, TITLE_SELECTORS, PRICE_EXTRACT_SELECTORS,
    QUANTITY_SELECTORS, BUY_INDICATORS, CRITICAL_ERROR_INDICATORS,
    PRODUCT_PAGE_INDICATORS
)

# Re-export for backward compatibility
def _now() -> str:
    """Backward compatibility function."""
    return get_timestamp()

def _safe_get_attr(elem, attr: str) -> Optional[str]:
    """Backward compatibility function."""
    from scraper.utils.helpers import safe_get_attribute
    return safe_get_attribute(elem, attr)


def main():
    """Main entry point - maintains original functionality."""
    print(f"[{_now()}] Scraper starting...")

    browser_scraper = BrowserScraper()
    available_products = browser_scraper.scrape_products()
    
    # New flow: attempt to purchase available products by clicking "Buy Now" buttons
    purchase_results = []
    if available_products and browser_scraper.availability_checker:
        print(f"[{_now()}] Found {len(available_products)} available products. Attempting to purchase...")
        
        for product in available_products:
            product_url = product.get('url')
            product_name = product.get('title', 'Unknown Product')
            
            if product_url:
                print(f"[{_now()}] Attempting to purchase: {product_name}")
                success, message = browser_scraper.availability_checker.click_buy_now_button(product_url)
                
                purchase_result = {
                    'product': product_name,
                    'url': product_url,
                    'purchase_success': success,
                    'purchase_message': message,
                    'timestamp': _now()
                }
                purchase_results.append(purchase_result)
                
                if success:
                    print(f"[{_now()}] Successfully initiated purchase for: {product_name}")
                else:
                    print(f"[{_now()}] Failed to purchase {product_name}: {message}")
            else:
                print(f"[{_now()}] No URL available for product: {product_name}")
    
    # Clean up browser resources
    if browser_scraper.webdriver_manager:
        browser_scraper.webdriver_manager.quit_driver()

    # Try to send notifications if notification_service module exists
    try:
        from notification_service import create_notification_service
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
        
        # Combine product and purchase information
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'available_products': available_products,
            'purchase_attempts': purchase_results,
            'summary': {
                'total_available': len(available_products),
                'purchase_attempts': len(purchase_results),
                'successful_purchases': sum(1 for r in purchase_results if r.get('purchase_success', False))
            }
        }
        
        filename = f"scraper_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            print(f"[{_now()}] Scraper results (including purchase attempts) saved to {filename}")
        except Exception as e:
            print(f"[{_now()}] Error saving results: {str(e)}")
    else:
        print(f"[{_now()}] No available products found.")

    # Print purchase summary
    if purchase_results:
        successful_purchases = sum(1 for r in purchase_results if r.get('purchase_success', False))
        print(f"\n[{_now()}] PURCHASE SUMMARY:")
        print(f"  Total products available: {len(available_products)}")
        print(f"  Purchase attempts made: {len(purchase_results)}")
        print(f"  Successful purchases: {successful_purchases}")
        print(f"  Failed purchases: {len(purchase_results) - successful_purchases}")
    
    print(f"[{_now()}] Scraper completed.")


if __name__ == "__main__":
    main()