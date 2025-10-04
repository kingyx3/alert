#!/usr/bin/env python3

import os
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time

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

class BrowserScraper:
    """Browser-based scraper that can handle dynamic content"""
    def __init__(self, base_url=None):
        # Use provided URL, environment variable, or default fallback
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = os.getenv(
                'SCRAPING_URL'
            )
        self.driver = None

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        if not SELENIUM_AVAILABLE:
            print(f"[{datetime.now()}] Selenium is not installed/available.")
            return False
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  # Disable images for faster loading
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            # Try to use the system chromedriver first
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            print(f"[{datetime.now()}] Failed to setup Chrome driver with system chromedriver: {str(e)}")
            try:
                # Fallback to webdriver manager if system driver fails
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return True
            except Exception as e2:
                print(f"[{datetime.now()}] Failed to setup Chrome driver with webdriver manager: {str(e2)}")
                return False

    def wait_for_products_to_load(self, timeout=20):
        """Wait for products to dynamically load on the page"""
        try:
            # Common selectors for Lazada product items
            product_selectors = [
                '[data-qa-locator="product-item"]',
                '.product-item',
                '.item-box',
                '.c2prKC',
                '.product',
                '[data-testid="product-item"]',
                '.item-card',
                '.product-card'
            ]
            
            for selector in product_selectors:
                try:
                    wait = WebDriverWait(self.driver, timeout)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        print(f"[{datetime.now()}] Found {len(elements)} products using selector: {selector}")
                        return elements
                except TimeoutException:
                    continue
            
            # If specific selectors don't work, try waiting for any elements with price indicators
            price_selectors = [
                '[class*="price"]',
                '[class*="Price"]',
                '[data-testid*="price"]'
            ]
            
            for selector in price_selectors:
                try:
                    wait = WebDriverWait(self.driver, timeout)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        print(f"[{datetime.now()}] Found {len(elements)} price elements, extracting parent containers")
                        # Get parent elements that likely contain product info
                        product_containers = []
                        for elem in elements:
                            parent = elem.find_element(By.XPATH, "./../..")
                            if parent not in product_containers:
                                product_containers.append(parent)
                        return product_containers[:20]  # Limit to first 20
                except TimeoutException:
                    continue
            
            print(f"[{datetime.now()}] No products found with known selectors within {timeout} seconds")
            return []
            
        except Exception as e:
            print(f"[{datetime.now()}] Error waiting for products: {str(e)}")
            return []

    def extract_product_info_from_element(self, element):
        """Extract product information from a selenium web element"""
        try:
            product = {}
            
            # Extract title
            title_selectors = [
                'h2', 'h3', '.title', '[data-qa-locator="product-name"]', 
                'a[title]', '[class*="title"]', '[class*="Title"]'
            ]
            title = ""
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.get_attribute('title') or title_elem.text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract image URL
            image_url = ""
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, 'img')
                image_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ""
            except NoSuchElementException:
                pass
            
            # Extract product URL
            product_url = ""
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, 'a')
                product_url = link_elem.get_attribute('href') or ""
            except NoSuchElementException:
                pass
            
            if title:  # Only return if we have some useful information
                product = {
                    'title': title or 'No title available',
                    'image': image_url,
                    'url': product_url,
                    'scraped_at': datetime.now().isoformat()
                }
                return product
                
        except Exception as e:
            print(f"[{datetime.now()}] Error extracting product info: {str(e)}")
        
        return None

    def check_product_availability(self, product_url):
        """Check product availability and extract price from individual product page"""
        try:
            if not product_url or not product_url.startswith('http'):
                # Convert relative URLs to absolute URLs
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://www.lazada.sg' + product_url
                else:
                    return False, "Invalid URL", None
            
            print(f"[{datetime.now()}] Checking availability and price for: {product_url}")
            self.driver.get(product_url)
            time.sleep(3)  # Wait for page to load and JS to execute
            
            # Extract price information
            price = self.extract_price_from_page()
            
            # Check availability using multiple methods
            is_available, availability_reason = self.check_availability_indicators()
            
            if is_available:
                status = f"Available{' - ' + price if price else ''}"
                return True, status, price
            else:
                print(f"Product not available: {product_url} ({availability_reason})")
                return False, f"Not available ({availability_reason})", price
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking product availability: {str(e)}")
            return False, f"Error: {str(e)}", None

    def extract_price_from_page(self):
        """Extract price information from the current product page"""
        try:
            # Common price selectors for e-commerce sites
            price_selectors = [
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
            
            for selector in price_selectors:
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in price_elements:
                        price_text = elem.text.strip()
                        # Look for text that contains currency symbols or price patterns
                        if price_text and any(symbol in price_text for symbol in ['$', '₹', '€', '£', '¥', 'S$', 'USD', 'SGD']):
                            # Clean up the price text
                            price_text = price_text.replace('\n', ' ').strip()
                            if len(price_text) < 50:  # Reasonable price text length
                                print(f"[{datetime.now()}] Found price: {price_text}")
                                return price_text
                except NoSuchElementException:
                    continue
                except Exception as e:
                    continue
            
            print(f"[{datetime.now()}] No price found on page")
            return None
            
        except Exception as e:
            print(f"[{datetime.now()}] Error extracting price: {str(e)}")
            return None

    def check_availability_indicators(self):
        """Check multiple indicators to determine product availability"""
        try:
            page_source = self.driver.page_source.lower()
            
            # Check for positive availability indicators
            buy_now_indicators = ['buy now', 'add to cart', 'purchase', 'order now', 'checkout']
            has_buy_indicators = any(indicator in page_source for indicator in buy_now_indicators)
            
            # Check for negative availability indicators
            unavailable_indicators = [
                'out of stock', 'sold out', 'not available', 'unavailable',
                'temporarily unavailable', 'stock out', 'no stock'
            ]
            has_unavailable_text = any(indicator in page_source for indicator in unavailable_indicators)
            
            # Check quantity selector state
            quantity_disabled = self.check_quantity_selector_disabled()
            
            # Determine availability based on multiple factors
            if has_unavailable_text:
                return False, "Out of stock text found"
            elif quantity_disabled:
                return False, "Quantity selector disabled"
            elif has_buy_indicators:
                return True, "Buy/Add to cart options available"
            else:
                return False, "No buy options found"
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking availability indicators: {str(e)}")
            return False, f"Error checking indicators: {str(e)}"

    def check_quantity_selector_disabled(self):
        """Check if quantity number picker/selector is disabled"""
        try:
            # Common selectors for quantity inputs
            quantity_selectors = [
                'input[type="number"]',
                '[class*="quantity"]',
                '[class*="qty"]',
                '[data-qa*="quantity"]',
                '[data-testid*="quantity"]',
                'select[class*="quantity"]',
                'input[name*="quantity"]',
                'input[name*="qty"]'
            ]
            
            for selector in quantity_selectors:
                try:
                    quantity_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in quantity_elements:
                        # Check if element is disabled
                        is_disabled = (
                            elem.get_attribute('disabled') is not None or
                            elem.get_attribute('readonly') is not None or
                            'disabled' in elem.get_attribute('class').lower() if elem.get_attribute('class') else False
                        )
                        if is_disabled:
                            print(f"[{datetime.now()}] Found disabled quantity selector")
                            return True
                except NoSuchElementException:
                    continue
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            print(f"[{datetime.now()}] Error checking quantity selector: {str(e)}")
            return False

    def scrape_products(self):
        """Scrape products using browser automation to handle dynamic content"""
        try:
            print(f"[{datetime.now()}] Starting browser-based scrape of store...")
            print(f"URL: {self.base_url}")

            if not SELENIUM_AVAILABLE:
                print(f"[{datetime.now()}] Selenium not available.")
                return []

            # Setup browser driver
            if not self.setup_driver():
                print(f"[{datetime.now()}] Failed to setup browser driver.")
                return []

            # Navigate to the page
            print(f"[{datetime.now()}] Navigating to the page...")
            self.driver.get(self.base_url)
            
            # Wait a moment for initial page load
            time.sleep(3)
            
            # Wait for products to load dynamically
            print(f"[{datetime.now()}] Waiting for products to load...")
            product_elements = self.wait_for_products_to_load(timeout=30)
            
            products = []
            if product_elements:
                print(f"[{datetime.now()}] Extracting information from {len(product_elements)} products...")
                for idx, element in enumerate(product_elements):
                    try:
                        product = self.extract_product_info_from_element(element)
                        if product:
                            products.append(product)
                    except Exception as e:
                        print(f"[{datetime.now()}] Error extracting product {idx}: {str(e)}")
                        continue
            
            if not products:
                print(f"[{datetime.now()}] No products found.")
            
            # Check availability for each product
            available_products = []
            available_count = 0
            
            print(f"[{datetime.now()}] Checking availability for {len(products)} products...")
            for product in products:
                if product.get('url'):
                    is_available, status, price = self.check_product_availability(product['url'])
                    product['availability_status'] = status
                    product['is_available'] = is_available
                    product['price'] = price  # Add price to product data
                    
                    if is_available:
                        available_products.append(product)
                        available_count += 1
                else:
                    product['availability_status'] = "No URL available"
                    product['is_available'] = False
                    product['price'] = None
            
            print(f"[{datetime.now()}] Browser scraping completed. Found {len(products)} products, {available_count} available.")
            
            # Display results
            self.display_results(available_products, available_count, len(products))
            
            return available_products

        except Exception as e:
            print(f"[{datetime.now()}] Browser scraper error: {str(e)}")
            return []
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    def display_results(self, products, available_count=None, total_count=None):
        """Display the scraped products in a formatted way"""
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
            print(f"\n{idx}. {product['title']}")
            if product['url']:
                print(f"   URL: {product['url']}")
            if product.get('price'):
                print(f"   Price: {product['price']}")
            if product.get('availability_status'):
                print(f"   Status: {product['availability_status']}")
            # if product['image']:
            #     print(f"   Image: {product['image']}")
            # print(f"   Scraped: {product['scraped_at']}")

        print(f"\n{'='*80}")
        print(f"Available products listed: {len(products)}")
        if available_count is not None and total_count is not None:
            print(f"Total products checked: {total_count}")
        print(f"{'='*80}\n")

def main():
    """Main function to run the scraper"""
    print(f"[{datetime.now()}] Scraper starting...")

    # Browser-only scraper
    browser_scraper = BrowserScraper()
    available_products = browser_scraper.scrape_products()

    # Store scraping results in a single text variable and send to Telegram
    try:
        from notification_service import create_notification_service
        
        # Create notification service
        notification_service = create_notification_service()
        
        # Format products into text and send notifications
        if available_products:
            print(f"[{datetime.now()}] Found {len(available_products)} available products")
            
            # Send notifications to Telegram chats from Firebase
            success = notification_service.notify_products(available_products)
            
            if success:
                print(f"[{datetime.now()}] Product notifications sent successfully")
            else:
                print(f"[{datetime.now()}] Failed to send product notifications")
        else:
            print(f"[{datetime.now()}] No available products found - no notifications sent")
            
    except ImportError:
        print(f"[{datetime.now()}] Notification service not available - running without notifications")
    except Exception as e:
        print(f"[{datetime.now()}] Error in notification service: {str(e)}")

    # Optional: Save results to JSON file
    if available_products:
        print('Available products:', len(available_products))
        filename = f"available_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{datetime.now()}] Available products saved to {filename}")
        except Exception as e:
            print(f"[{datetime.now()}] Error saving results: {str(e)}")
    else:
        print(f"[{datetime.now()}] No available products found.")

    print(f"[{datetime.now()}] Scraper completed.")

if __name__ == "__main__":
    main()