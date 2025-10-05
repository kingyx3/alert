#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ---------- Module-level constants (selectors / timeouts) ----------
DEFAULT_WINDOW_SIZE = "1920,1080"
SYSTEM_CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

# Common selectors for listing pages
PRODUCT_SELECTORS = [
    '[data-qa-locator="product-item"]',
    '.product-item',
    '.item-box',
    '.c2prKC',
    '.product',
    '[data-testid="product-item"]',
    '.item-card',
    '.product-card'
]

PRICE_SELECTORS = [
    '[class*="price"]',
    '[class*="Price"]',
    '[data-testid*="price"]'
]

TITLE_SELECTORS = [
    'h2', 'h3', '.title', '[data-qa-locator="product-name"]',
    'a[title]', '[class*="title"]', '[class*="Title"]'
]

PRICE_EXTRACT_SELECTORS = [
    '[class*="price"]',
    '[class*="Price"]',
    '[data-qa-locator*="price"]',
    '[data-testid*="price"]',
    '.price',
    '.current-price',
    '.sale-price',
    '.final-price',
    'span[class*="price"]',
    'div[class*="price"]',
    '.product-price',
    '.price-current'
]

BUY_INDICATORS = [
    'buy now', 'buy', 'add to cart', 'add to bag', 'purchase', 'order now',
    'add-to-cart', 'buy-now', 'add item', 'order', 'checkout', 'get it now'
]  # used in availability detection

CRITICAL_ERROR_INDICATORS = [
    'page not found', '404 error', 'server error', '500 error',
    'network error', 'connection failed',
    'access denied', 'forbidden', 'not available in your region',
    'blocked', 'captcha required', 'bot detection', 'unusual traffic detected',
    'temporarily unavailable', 'site maintenance', 'under maintenance',
    'internal server error', 'bad gateway', 'service unavailable'
]

PRODUCT_PAGE_INDICATORS = [
    'price', 'product', 'buy', 'cart', 'add to cart', 'purchase', 'order',
    'add-to-cart', 'buy now', 'buy-now', 'quantity', 'qty', 'delivery',
    'shipping', 'checkout', 'item', 'sku', 'stock', 'available',
    'pdp-', 'lazada', 'item-detail', 'product-detail', 'current-price',
    'original-price', 'sale-price', 'final-price',
    's$', '$', '€', '£', '¥', 'usd', 'sgd', 'price_', 'currency',
    'rating', 'review', 'star', 'seller', 'brand', 'description',
    'specification', 'warranty', 'return', 'exchange'
]

QUANTITY_SELECTORS = [
    'input[type="number"]',
    '[class*="quantity"]',
    '[class*="qty"]',
    '[data-qa*="quantity"]',
    '[data-testid*="quantity"]',
    'select[class*="quantity"]',
    'input[name*="quantity"]',
    'input[name*="qty"]'
]

# ---------- Helper functions ----------
def _now() -> str:
    return datetime.now().isoformat()


def _safe_get_attr(elem, attr: str) -> Optional[str]:
    """Return attribute value or None safely."""
    try:
        return elem.get_attribute(attr)
    except Exception:
        return None


# ---------- BrowserScraper class ----------
class BrowserScraper:
    """Browser-based scraper that can handle dynamic content."""

    def __init__(self, base_url: Optional[str] = None):
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = os.getenv('SCRAPING_URL')
        self.driver = None

    # ----------------- Driver setup -----------------
    def setup_driver(self) -> bool:
        """Setup Chrome driver with recommended options and return success state."""
        if not SELENIUM_AVAILABLE:
            print(f"[{_now()}] Selenium is not installed/available.")
            return False

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--window-size={DEFAULT_WINDOW_SIZE}')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )

        # Try system chromedriver first, then webdriver-manager fallback
        try:
            service = Service(SYSTEM_CHROMEDRIVER_PATH)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            print(f"[{_now()}] Failed to setup Chrome driver with system chromedriver: {str(e)}")
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return True
            except Exception as e2:
                print(f"[{_now()}] Failed to setup Chrome driver with webdriver manager: {str(e2)}")
                return False

    # ----------------- Page readiness and validation -----------------
    def wait_for_page_ready(self, expected_url: Optional[str] = None, timeout: int = 10) -> bool:
        """Wait for document readyState == 'complete' and do a minimal validation."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(1)  # allow JS to start executing
            if expected_url:
                return self.validate_page_loaded(expected_url)
            return True
        except TimeoutException:
            print(f"[{_now()}] Timeout waiting for page to be ready")
            return False
        except Exception as e:
            print(f"[{_now()}] Error waiting for page ready: {str(e)}")
            return False

    def validate_page_loaded(self, expected_url: Optional[str]) -> bool:
        """Validate that the current page contains meaningful product-related content."""
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            if not current_url or current_url == "data:,":
                print(f"[{_now()}] Page validation failed: Invalid current URL: {current_url}")
                return False

            if not page_source or len(page_source.strip()) < 50:
                print(f"[{_now()}] Page validation failed: Page content too short or empty")
                return False

            page_lower = page_source.lower()

            # Critical error indicators
            found_critical = [i for i in CRITICAL_ERROR_INDICATORS if i in page_lower]
            if found_critical:
                print(f"[{_now()}] Page validation failed: Error page detected - {found_critical}")
                return False

            title_lower = (self.driver.title or "").lower()
            ambiguous_error_phrases = ['error occurred', 'something went wrong', 'try again later']
            for phrase in ambiguous_error_phrases:
                if phrase in title_lower:
                    print(f"[{_now()}] Page validation failed: Error phrase in title - '{phrase}'")
                    return False
                # look for phrase in obvious error markup contexts
                contexts = [
                    f'<h1>{phrase}</h1>', f'<h2>{phrase}</h2>', f'<h3>{phrase}</h3>',
                    f'<div class="error">{phrase}', f'<div class="message">{phrase}',
                    f'<p class="error">{phrase}', f'<span class="error">{phrase}'
                ]
                if any(context in page_lower for context in contexts):
                    print(f"[{_now()}] Page validation failed: Error message in error context - '{phrase}'")
                    return False

            # Check for product indicators
            found_indicators = [ind for ind in PRODUCT_PAGE_INDICATORS if ind in page_lower]
            if not found_indicators:
                print(f"[{_now()}] Page validation failed: No product-related content found")
                print(f"[{_now()}] Page title: {self.driver.title}")
                print(f"[{_now()}] Page source length: {len(page_source)}")
                sample_content = page_source[:500] if len(page_source) > 500 else page_source
                print(f"[{_now()}] Page content sample: {sample_content[:200]}...")
                return False

            print(f"[{_now()}] Page validation passed for: {expected_url}")
            print(f"[{_now()}] Found indicators: {found_indicators[:5]}...")
            return True
        except Exception as e:
            print(f"[{_now()}] Error validating page load: {str(e)}")
            return False

    # ----------------- Product-list extraction and waiting -----------------
    def wait_for_products_to_load(self, timeout: int = 20) -> List[Any]:
        """
        Wait for known product selectors; fallback to price selectors and extract parent containers.
        Returns a list of selenium web elements (product containers) or empty list.
        """
        try:
            for selector in PRODUCT_SELECTORS:
                try:
                    wait = WebDriverWait(self.driver, timeout)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        print(f"[{_now()}] Found {len(elements)} products using selector: {selector}")
                        return elements
                except TimeoutException:
                    continue

            # fallback: wait for price elements and use their parent containers
            for selector in PRICE_SELECTORS:
                try:
                    wait = WebDriverWait(self.driver, timeout)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        print(f"[{_now()}] Found {len(elements)} price elements, extracting parent containers")
                        product_containers = []
                        for elem in elements:
                            try:
                                parent = elem.find_element(By.XPATH, "./../..")
                                if parent not in product_containers:
                                    product_containers.append(parent)
                            except Exception:
                                continue
                        return product_containers[:20]
                except TimeoutException:
                    continue

            print(f"[{_now()}] No products found with known selectors within {timeout} seconds")
            return []
        except Exception as e:
            print(f"[{_now()}] Error waiting for products: {str(e)}")
            return []

    # ----------------- Extract product info -----------------
    def extract_product_info_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract title, image and url from a product container element."""
        try:
            title = ""
            for selector in TITLE_SELECTORS:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = _safe_get_attr(title_elem, 'title') or (title_elem.text or "").strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue

            image_url = ""
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, 'img')
                image_url = _safe_get_attr(img_elem, 'src') or _safe_get_attr(img_elem, 'data-src') or ""
            except NoSuchElementException:
                pass

            product_url = ""
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, 'a')
                product_url = _safe_get_attr(link_elem, 'href') or ""
            except NoSuchElementException:
                pass

            if title:
                product = {
                    'title': title or 'No title available',
                    'image': image_url,
                    'url': product_url,
                    'scraped_at': datetime.now().isoformat()
                }
                return product
        except Exception as e:
            print(f"[{_now()}] Error extracting product info: {str(e)}")
        return None

    # ----------------- Price extraction & availability -----------------
    def extract_price_from_page(self) -> Optional[str]:
        """Try many selectors and return first reasonable price-like string found."""
        try:
            for selector in PRICE_EXTRACT_SELECTORS:
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in price_elements:
                        price_text = (elem.text or "").strip()
                        if price_text and any(symbol in price_text for symbol in ['$', '₹', '€', '£', '¥', 'S$', 'USD', 'SGD']):
                            price_text = price_text.replace('\n', ' ').strip()
                            if len(price_text) < 50:
                                print(f"[{_now()}] Found price: {price_text}")
                                return price_text
                except NoSuchElementException:
                    continue
                except Exception:
                    continue
            print(f"[{_now()}] No price found on page")
            return None
        except Exception as e:
            print(f"[{_now()}] Error extracting price: {str(e)}")
            return None

    def check_availability_indicators(self) -> Tuple[bool, str]:
        """Check presence of buy/add-to-cart style indicators in the page source."""
        try:
            page_source = (self.driver.page_source or "").lower()
            has_buy_indicators = any(indicator in page_source for indicator in BUY_INDICATORS)
            if has_buy_indicators:
                return True, "Buy/Add to cart options available"
            else:
                return False, "No buy options found"
        except Exception as e:
            print(f"[{_now()}] Error checking availability indicators: {str(e)}")
            return False, f"Error checking indicators: {str(e)}"

    def check_quantity_selector_disabled(self) -> bool:
        """Check if any quantity inputs are disabled/read-only."""
        try:
            for selector in QUANTITY_SELECTORS:
                try:
                    quantity_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in quantity_elements:
                        try:
                            class_attr = (elem.get_attribute('class') or "").lower()
                            is_disabled = (
                                elem.get_attribute('disabled') is not None or
                                elem.get_attribute('readonly') is not None or
                                ('disabled' in class_attr if class_attr else False)
                            )
                            if is_disabled:
                                print(f"[{_now()}] Found disabled quantity selector")
                                return True
                        except Exception:
                            continue
                except NoSuchElementException:
                    continue
                except Exception:
                    continue
            return False
        except Exception as e:
            print(f"[{_now()}] Error checking quantity selector: {str(e)}")
            return False

    # ----------------- Check single product page -----------------
    def check_product_availability(self, product_url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Visit product_url, validate page loaded, attempt price extraction and availability check.
        Returns (is_available, status_string, price_or_None)
        """
        try:
            if not product_url or not product_url.startswith('http'):
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://www.lazada.sg' + product_url
                else:
                    return False, "Invalid URL", None

            print(f"[{_now()}] Checking availability and price for: {product_url}")
            self.driver.get(product_url)

            if not self.wait_for_page_ready(product_url):
                print(f"[{_now()}] Page failed to load correctly for: {product_url}")
                return False, "Page failed to load correctly", None

            price = self.extract_price_from_page()
            is_available, availability_reason = self.check_availability_indicators()

            if is_available:
                status = f"Available{' - ' + price if price else ''}"
                return True, status, price
            else:
                print(f"Product not available: {product_url} ({availability_reason})")
                return False, f"Not available ({availability_reason})", price

        except Exception as e:
            print(f"[{_now()}] Error checking product availability: {str(e)}")
            return False, f"Error: {str(e)}", None

    # ----------------- Main scraping flow -----------------
    def scrape_products(self) -> List[Dict[str, Any]]:
        """Main flow: setup driver, load base_url, find product containers, extract info, check availability."""
        try:
            print(f"[{_now()}] Starting browser-based scrape of store...")
            print(f"URL: {self.base_url}")

            if not SELENIUM_AVAILABLE:
                print(f"[{_now()}] Selenium not available.")
                return []

            if not self.setup_driver():
                print(f"[{_now()}] Failed to setup browser driver.")
                return []

            print(f"[{_now()}] Navigating to the page...")
            self.driver.get(self.base_url)

            print(f"[{_now()}] Waiting for page to be ready...")
            if not self.wait_for_page_ready(self.base_url):
                print(f"[{_now()}] Page failed to load properly")
                return []

            print(f"[{_now()}] Waiting for products to load...")
            product_elements = self.wait_for_products_to_load(timeout=30)

            products: List[Dict[str, Any]] = []
            if product_elements:
                print(f"[{_now()}] Extracting information from {len(product_elements)} products...")
                for idx, element in enumerate(product_elements):
                    try:
                        product = self.extract_product_info_from_element(element)
                        if product:
                            products.append(product)
                    except Exception as e:
                        print(f"[{_now()}] Error extracting product {idx}: {str(e)}")
                        continue

            if not products:
                print(f"[{_now()}] No products found.")

            available_products: List[Dict[str, Any]] = []
            available_count = 0

            print(f"[{_now()}] Checking availability for {len(products)} products...")
            for product in products:
                if product.get('url'):
                    is_available, status, price = self.check_product_availability(product['url'])
                    product['availability_status'] = status
                    product['is_available'] = is_available
                    product['price'] = price
                    if is_available:
                        available_products.append(product)
                        available_count += 1
                else:
                    product['availability_status'] = "No URL available"
                    product['is_available'] = False
                    product['price'] = None

            print(f"[{_now()}] Browser scraping completed. Found {len(products)} products, {available_count} available.")
            self.display_results(available_products, available_count, len(products))
            return available_products

        except Exception as e:
            print(f"[{_now()}] Browser scraper error: {str(e)}")
            return []
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass

    # ----------------- Results display -----------------
    def display_results(self, products: List[Dict[str, Any]], available_count: Optional[int] = None,
                        total_count: Optional[int] = None) -> None:
        """Display the scraped products in a formatted way (keeps original print behavior)."""
        print(f"\n{'='*80}")
        print(f"STORE SCRAPING RESULTS (BROWSER) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        if available_count is not None and total_count is not None:
            print(f"Available products: {available_count}/{total_count}")
            print(f"{'='*80}")

        if not products:
            print("No available products found.")
            return

        for idx, product in enumerate(products, 1):
            print(f"\n{idx}. {product['title']} ({product['price']})")
            if product.get('url'):
                print(f"   URL: {product['url']}")
            if product.get('availability_status'):
                print(f"   Status: {product['availability_status']}")

        print(f"\n{'='*80}")
        print(f"Available products listed: {len(products)}")
        if available_count is not None and total_count is not None:
            print(f"Total products checked: {total_count}")
        print(f"{'='*80}\n")


# ---------- Main entry point ----------
def main():
    print(f"[{_now()}] Scraper starting...")

    browser_scraper = BrowserScraper()
    available_products = browser_scraper.scrape_products()

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