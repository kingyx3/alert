#!/usr/bin/env python3

import requests
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
class BaseScraper:
    """Base class with common scraper functionality"""
    
    def __init__(self):
        self.base_url = "https://www.lazada.sg/pokemon-store-online-singapore/?spm=a2o42.10453684.0.0.68ae5edfACSkfR&q=All-Products&shop_category_ids=762252&from=wangpu&sc=KVUG&search_scenario=store&src=store_sections&hideSectionHeader=true&shopId=2056827"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def check_product_availability(self, product_url):
        """Check if a product page contains 'Buy Now' button text"""
        try:
            if not product_url or not product_url.startswith('http'):
                # Convert relative URLs to absolute URLs
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://www.lazada.sg' + product_url
                else:
                    return False, "Invalid URL"
            
            print(f"[{datetime.now()}] Checking availability for: {product_url}")
            response = requests.get(product_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Parse the product page content
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for "Buy Now" button text
            has_buy_now = 'buy now' in page_text
            
            if has_buy_now:
                return True, "Available - Buy Now button found"
            else:
                return False, "Not available - Buy Now button not found"
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking product availability: {str(e)}")
            return False, f"Error: {str(e)}"

    def analyze_page_structure(self, soup):
        """Analyze the page structure to understand the layout"""
        print(f"[{datetime.now()}] Page title: {soup.title.string if soup.title else 'No title'}")

        # Count common elements
        divs = len(soup.find_all('div'))
        spans = len(soup.find_all('span'))
        links = len(soup.find_all('a'))
        images = len(soup.find_all('img'))

        print(f"[{datetime.now()}] Page structure - Divs: {divs}, Spans: {spans}, Links: {links}, Images: {images}")

        # Look for potential product containers
        potential_containers = soup.find_all('div', class_=lambda x: x and any(keyword in x.lower() for keyword in ['product', 'item', 'card', 'box']))
        print(f"[{datetime.now()}] Found {len(potential_containers)} potential product containers")

    def display_results(self, products, available_count=None, total_count=None, scraper_type=""):
        """Display the scraped products in a formatted way"""
        print(f"\n{'='*80}")
        print(f"POKEMON STORE SCRAPING RESULTS{' (' + scraper_type + ')' if scraper_type else ''} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        if available_count is not None and total_count is not None:
            print(f"Available products (with 'Buy Now' button): {available_count}/{total_count}")
            print(f"{'='*80}")

        if not products:
            print("No available products found.")
            return

        for idx, product in enumerate(products, 1):
            print(f"\n{idx}. {product['title']}")
            print(f"   Price: {product.get('price', 'Price not available')}")
            if product.get('url'):
                print(f"   URL: {product['url']}")
            if product.get('availability_status'):
                print(f"   Status: {product['availability_status']}")
            if product.get('image'):
                print(f"   Image: {product['image']}")
            print(f"   Scraped: {product['scraped_at']}")

        print(f"\n{'='*80}")
        print(f"Available products listed: {len(products)}")
        if available_count is not None and total_count is not None:
            print(f"Total products checked: {total_count}")
        print(f"{'='*80}\n")

class BrowserScraper(BaseScraper):
    """Browser-based scraper that can handle dynamic content"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.lazada.sg/pokemon-store-online-singapore/?spm=a2o42.10453684.0.0.28e55edfSHrAL6&q=All-Products&shop_category_ids=762253&from=wangpu&sc=KVUG&search_scenario=store&src=store_sections&hideSectionHeader=true&shopId=2056827"
        self.driver = None

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not available")
        
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
            
            # Extract price
            price_selectors = [
                '.price', '[data-qa-locator="product-price"]', '.current-price', 
                '.sale-price', '[class*="price"]', '[class*="Price"]'
            ]
            price = ""
            for selector in price_selectors:
                try:
                    price_elem = element.find_element(By.CSS_SELECTOR, selector)
                    price = price_elem.text.strip()
                    if price:
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
            
            if title or price:  # Only return if we have some useful information
                product = {
                    'title': title or 'No title available',
                    'price': price or 'Price not available',
                    'image': image_url,
                    'url': product_url,
                    'scraped_at': datetime.now().isoformat()
                }
                return product
                
        except Exception as e:
            print(f"[{datetime.now()}] Error extracting product info: {str(e)}")
        
        return None

    def check_product_availability(self, product_url):
        """Check if a product page contains 'Buy Now' button text using Selenium"""
        try:
            if not product_url or not product_url.startswith('http'):
                # Convert relative URLs to absolute URLs
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://www.lazada.sg' + product_url
                else:
                    return False, "Invalid URL"
            
            print(f"[{datetime.now()}] Checking availability for: {product_url}")
            self.driver.get(product_url)
            time.sleep(2)  # Wait for page to load
            
            # Get the page source and check for specific text
            page_source = self.driver.page_source.lower()
            
            # Check for "Buy Now" button text
            has_buy_now = 'buy now' in page_source
            
            if has_buy_now:
                return True, "Available - Buy Now button found"
            else:
                return False, "Not available - Buy Now button not found"
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking product availability: {str(e)}")
            return False, f"Error: {str(e)}"

    def scrape_products(self):
        """Scrape products using browser automation to handle dynamic content"""
        try:
            print(f"[{datetime.now()}] Starting browser-based scrape of Pokemon Store...")
            print(f"URL: {self.base_url}")

            if not SELENIUM_AVAILABLE:
                print(f"[{datetime.now()}] Selenium not available, falling back to basic scraper...")
                fallback_scraper = Scraper()
                return fallback_scraper.scrape_products()

            # Setup browser driver
            if not self.setup_driver():
                print(f"[{datetime.now()}] Failed to setup browser, falling back to basic scraper...")
                fallback_scraper = Scraper()
                return fallback_scraper.scrape_products()

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
                print(f"[{datetime.now()}] No products found with browser scraper, analyzing page...")
                # Get page source and analyze
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                self.analyze_page_structure(soup)
            
            # Check availability for each product
            available_products = []
            available_count = 0
            
            print(f"[{datetime.now()}] Checking availability for {len(products)} products...")
            for product in products:
                if product.get('url'):
                    is_available, status = self.check_product_availability(product['url'])
                    product['availability_status'] = status
                    product['is_available'] = is_available
                    
                    if is_available:
                        available_products.append(product)
                        available_count += 1
                else:
                    product['availability_status'] = "No URL available"
                    product['is_available'] = False
            
            print(f"[{datetime.now()}] Browser scraping completed. Found {len(products)} products, {available_count} available.")
            
            # Display results
            self.display_results(available_products, available_count, len(products), "BROWSER")
            
            return available_products

        except Exception as e:
            print(f"[{datetime.now()}] Browser scraper error: {str(e)}")
            print(f"[{datetime.now()}] Falling back to basic scraper...")
            fallback_scraper = Scraper()
            return fallback_scraper.scrape_products()
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

class Scraper(BaseScraper):
    def __init__(self):
        super().__init__()

    def scrape_products(self):
        """Scrape products from the Pokemon Store"""
        try:
            print(f"[{datetime.now()}] Starting scrape of Pokemon Store...")
            print(f"URL: {self.base_url}")

            # Make request to the store page
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            print(f"[{datetime.now()}] Successfully retrieved page (Status: {response.status_code})")

            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find product containers - Lazada typically uses specific classes for product listings
            products = []

            # Look for common Lazada product selectors
            product_selectors = [
                '[data-qa-locator="product-item"]',
                '.product-item',
                '.item-box',
                '.c2prKC',  # Common Lazada product class
                '.product'
            ]

            product_elements = []
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements:
                    product_elements = elements
                    print(f"[{datetime.now()}] Found {len(elements)} products using selector: {selector}")
                    break

            if not product_elements:
                # If no specific selectors work, try to find products by looking for price elements
                price_elements = soup.find_all(['span', 'div'], class_=lambda x: x and ('price' in x.lower() if isinstance(x, str) else False))
                if price_elements:
                    print(f"[{datetime.now()}] Found {len(price_elements)} price elements, attempting to extract products")
                    product_elements = [elem.find_parent() for elem in price_elements[:20]]  # Limit to first 20

            # Extract product information
            for idx, element in enumerate(product_elements):
                if not element:
                    continue

                try:
                    product = self.extract_product_info(element)
                    if product:
                        products.append(product)

                except Exception as e:
                    print(f"[{datetime.now()}] Error extracting product {idx}: {str(e)}")
                    continue

            # If we still don't have products, let's examine the page structure
            if not products:
                print(f"[{datetime.now()}] No products found with standard selectors. Analyzing page structure...")
                self.analyze_page_structure(soup)

                # Try a more generic approach
                links = soup.find_all('a', href=True)
                product_links = [link for link in links if '/products/' in link.get('href', '') or 'item' in link.get('href', '').lower()]

                for link in product_links[:10]:  # Limit to first 10
                    try:
                        product = {
                            'title': link.get_text(strip=True) or 'No title available',
                            'url': link.get('href'),
                            'price': 'Price not available',
                            'image': '',
                            'scraped_at': datetime.now().isoformat()
                        }
                        if product['title'] and len(product['title']) > 3:
                            products.append(product)
                    except Exception as e:
                        continue

            # Check availability for each product
            available_products = []
            available_count = 0
            
            print(f"[{datetime.now()}] Checking availability for {len(products)} products...")
            for product in products:
                if product.get('url'):
                    is_available, status = self.check_product_availability(product['url'])
                    product['availability_status'] = status
                    product['is_available'] = is_available
                    
                    if is_available:
                        available_products.append(product)
                        available_count += 1
                else:
                    product['availability_status'] = "No URL available"
                    product['is_available'] = False

            print(f"[{datetime.now()}] Scraping completed. Found {len(products)} products, {available_count} available.")

            # Display results
            self.display_results(available_products, available_count, len(products), "BASIC")

            return available_products

        except requests.RequestException as e:
            print(f"[{datetime.now()}] Request error: {str(e)}")
            return []
        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error: {str(e)}")
            return []

    def extract_product_info(self, element):
        """Extract product information from a product element"""
        product = {}

        # Extract title
        title_selectors = ['h2', 'h3', '.title', '[data-qa-locator="product-name"]', 'a']
        title = ""
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                title = title_elem.get_text(strip=True)
                break

        # Extract price
        price_selectors = ['.price', '[data-qa-locator="product-price"]', '.current-price', '.sale-price']
        price = ""
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem and price_elem.get_text(strip=True):
                price = price_elem.get_text(strip=True)
                break

        # Extract image
        img_elem = element.select_one('img')
        image_url = ""
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src') or ""

        # Extract product URL
        link_elem = element.select_one('a')
        product_url = ""
        if link_elem:
            product_url = link_elem.get('href', "")

        if title:
            product = {
                'title': title or 'No title available',
                'price': price or 'Price not available',
                'image': image_url,
                'url': product_url,
                'scraped_at': datetime.now().isoformat()
            }
            return product

        return None

def main():
    """Main function to run the scraper"""
    print(f"[{datetime.now()}] Scraper starting...")

    # Try browser scraper first for dynamic content handling
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