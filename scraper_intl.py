#!/usr/bin/env python3
"""
International scraper module for ETB sites using custom selenium-based scraping.

This module uses the SCRAPING_URL_INTL_ETB environment variable and implements
custom scraping components specifically designed for international ETB e-commerce sites.

Dependencies:
    Install required packages with: pip install -r requirements_intl.txt
    
Requirements:
    - selenium>=4.36.0
    - webdriver-manager>=4.0.2
    - Chrome browser (for WebDriver)
"""

import os
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

# Selenium imports with fallbacks
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    # Mock classes to prevent import errors
    class Options:
        def add_argument(self, arg): pass
    class Service:
        def __init__(self, path): pass
    class By:
        CSS_SELECTOR = "css selector"
        XPATH = "xpath"
        CLASS_NAME = "class name"
        ID = "id"
        TAG_NAME = "tag name"
    class WebDriverWait:
        def __init__(self, driver, timeout): pass
        def until(self, condition): return []
    class EC:
        @staticmethod
        def presence_of_all_elements_located(locator): return lambda driver: []
    class TimeoutException(Exception):
        pass
    webdriver = None

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().isoformat()


class ETBWebDriverManager:
    """Custom WebDriver manager for ETB sites."""
    
    def __init__(self):
        self.driver = None
        
    def setup_driver(self) -> bool:
        """Setup Chrome driver optimized for ETB sites."""
        if not SELENIUM_AVAILABLE:
            print(f"[{get_timestamp()}] Selenium is not installed/available.")
            return False

        chrome_options = self._get_chrome_options()
        
        # Try system chromedriver first, then webdriver-manager fallback
        if self._try_system_chromedriver(chrome_options):
            return True
        elif self._try_webdriver_manager(chrome_options):
            return True
        else:
            return False
    
    def _get_chrome_options(self) -> Options:
        """Configure Chrome options specifically for ETB sites."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        # Add ETB-specific headers
        chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
        return chrome_options
    
    def _try_system_chromedriver(self, chrome_options: Options) -> bool:
        """Try to setup driver with system chromedriver."""
        try:
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # Disable automation detection for ETB sites
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to setup Chrome driver with system chromedriver: {str(e)}")
            return False
    
    def _try_webdriver_manager(self, chrome_options: Options) -> bool:
        """Try to setup driver with webdriver-manager."""
        if not WEBDRIVER_MANAGER_AVAILABLE:
            return False
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # Disable automation detection for ETB sites
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to setup Chrome driver with webdriver manager: {str(e)}")
            return False
    
    def quit_driver(self):
        """Quit the WebDriver instance."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"[{get_timestamp()}] Error quitting driver: {str(e)}")
            finally:
                self.driver = None


class ETBProductExtractor:
    """Custom product extractor for ETB e-commerce sites."""
    
    # ETB-specific selectors for international sites
    ETB_PRODUCT_SELECTORS = [
        "div.product--feNDW"
    ]
    
    ETB_TITLE_SELECTORS = [
        '[data-product-name]',
        '.product-name', 
        '.product-title',
        '.item-title',
        '.item-name',
        'h1', 'h2', 'h3', 'h4',
        '.title',
        '[class*="title"]',
        '[class*="name"]',
        'a[title]',
        '.etb-title',
        '.etb-product-name'
    ]
    
    ETB_PRICE_SELECTORS = [
        '[data-price]',
        '.price',
        '.product-price', 
        '.item-price',
        '.current-price',
        '.sale-price',
        '.final-price',
        '.price-current',
        '[class*="price"]',
        '[class*="Price"]',
        'span[class*="price"]',
        'div[class*="price"]',
        '.etb-price',
        '.etb-product-price'
    ]
    
    ETB_IMAGE_SELECTORS = [
        '.product-image img',
        '.item-image img',
        '.product-img img', 
        '.product-photo img',
        '[data-product-image]',
        '.image img',
        'img[data-src]',
        'img[src]',
        '.etb-image img',
        '.etb-product-img img'
    ]
    
    ETB_LINK_SELECTORS = [
        '.product-link',
        '.item-link',
        'a[href*="/product"]',
        'a[href*="/item"]',
        'a[href*="/p/"]',
        'a[data-product-url]',
        '.etb-product-link',
        '.etb-item-link'
    ]
    
    def __init__(self, driver):
        self.driver = driver
    
    def wait_for_products_to_load(self, timeout: int = 30) -> List[Any]:
        """Wait for ETB product elements to load."""
        if not SELENIUM_AVAILABLE or not self.driver:
            return []
            
        try:
            print(f"[{get_timestamp()}] Waiting for ETB products to load...")
            
            # Wait for page to be ready first
            time.sleep(2)
            
            # Try ETB-specific selectors with individual timeouts
            for selector in self.ETB_PRODUCT_SELECTORS:
                try:
                    wait = WebDriverWait(self.driver, 2)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        print(f"[{get_timestamp()}] Found {len(elements)} products using selector: {selector}")
                        return elements
                except TimeoutException:
                    continue
                except Exception as e:
                    print(f"[{get_timestamp()}] Error with selector {selector}: {str(e)}")
                    continue
            
            # If no products found with specific selectors, try fallback strategies
            print(f"[{get_timestamp()}] No products found with specific selectors, trying fallback approaches...")
            return self._try_fallback_product_detection()
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error waiting for ETB products: {str(e)}")
            return []
    
    def _try_fallback_product_detection(self) -> List[Any]:
        """Try fallback strategies to detect products when specific selectors fail."""
        try:
            # Strategy 1: Find elements by price selectors and get their containers
            price_elements = self._find_elements_by_price()
            if price_elements:
                return price_elements
            
            # Strategy 2: Find elements containing common e-commerce patterns
            pattern_elements = self._find_elements_by_patterns()
            if pattern_elements:
                return pattern_elements
            
            # Strategy 3: Debug page structure to understand what we're working with
            self._debug_page_structure()
            
            # Strategy 4: Try generic container detection
            generic_elements = self._find_generic_containers()
            if generic_elements:
                return generic_elements
                
            return []
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in fallback detection: {str(e)}")
            return []
    
    def _find_elements_by_price(self) -> List[Any]:
        """Find product containers by looking for price elements."""
        try:
            print(f"[{get_timestamp()}] Trying price-based product detection...")
            for price_selector in self.ETB_PRICE_SELECTORS[:5]:  # Try first 5 price selectors
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, price_selector)
                    if price_elements:
                        # Get parent containers of price elements
                        containers = []
                        for price_elem in price_elements[:20]:  # Limit to first 20 to avoid performance issues
                            try:
                                # Try to get a reasonable container (parent or grandparent)
                                container = self._get_product_container(price_elem)
                                if container and container not in containers:
                                    containers.append(container)
                            except:
                                continue
                        
                        if containers:
                            print(f"[{get_timestamp()}] Found {len(containers)} products via price selector: {price_selector}")
                            return containers
                except:
                    continue
        except Exception as e:
            print(f"[{get_timestamp()}] Error in price-based detection: {str(e)}")
        return []
    
    def _find_elements_by_patterns(self) -> List[Any]:
        """Find elements that contain common e-commerce patterns."""
        try:
            print(f"[{get_timestamp()}] Trying pattern-based product detection...")
            # Look for divs/elements that contain links with meaningful href patterns
            try:
                # Find all links that look like product links
                links = self.driver.find_elements(By.TAG_NAME, "a")
                product_links = []
                for link in links:
                    href = link.get_attribute('href')
                    if href and self._href_looks_like_product(href):
                        product_links.append(link)
                
                if len(product_links) >= 2:
                    # Get parent containers of product links
                    containers = []
                    for link in product_links:
                        try:
                            parent = link.find_element(By.XPATH, "..")
                            if parent and parent not in containers:
                                containers.append(parent)
                        except:
                            containers.append(link)
                    
                    if len(containers) >= 2:
                        print(f"[{get_timestamp()}] Found {len(containers)} products via product link detection")
                        return containers
            except:
                pass
            
            # Look for elements that contain both text patterns and links
            patterns = [
                "div:has(a[href])",  # Divs with links
                "article",  # Articles (common for products)
                "li:has(a)",  # List items with links
                "[class*='item']:has(a)",  # Items with links
                "[class*='card']:has(a)",  # Cards with links
            ]
            
            for pattern in patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    if elements and len(elements) >= 2:  # Must find multiple elements
                        # Filter elements that look like products
                        product_like = []
                        for elem in elements[:50]:  # Limit for performance
                            if self._element_looks_like_product(elem):
                                product_like.append(elem)
                        
                        if len(product_like) >= 2:  # Need at least a couple products
                            print(f"[{get_timestamp()}] Found {len(product_like)} products via pattern: {pattern}")
                            return product_like
                except:
                    continue
        except Exception as e:
            print(f"[{get_timestamp()}] Error in pattern-based detection: {str(e)}")
        return []
    
    def _href_looks_like_product(self, href: str) -> bool:
        """Check if href looks like a product link."""
        if not href or href == '#':
            return False
        
        # Common product URL patterns
        product_patterns = [
            '/product', '/item', '/shop', '/buy', '/p/', '/goods',
            'product=', 'item=', 'id=', 'sku=', '/widget'
        ]
        
        href_lower = href.lower()
        for pattern in product_patterns:
            if pattern in href_lower:
                return True
        
        return False
    
    def _find_generic_containers(self) -> List[Any]:
        """Find generic container elements that might contain products."""
        try:
            print(f"[{get_timestamp()}] Trying generic container detection...")
            # Look for repetitive structures (common in product listings)
            selectors = [
                "div > div > div",  # Nested divs
                "ul > li",  # List items
                "div[class]",  # Divs with classes
                "section > div",  # Sections with divs
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 10:  # Must be many similar elements
                        # Take a sample and check if they contain links/text
                        sample = elements[:20]
                        valid_elements = []
                        for elem in sample:
                            if self._element_has_content(elem):
                                valid_elements.append(elem)
                        
                        if len(valid_elements) > 5:
                            print(f"[{get_timestamp()}] Found {len(valid_elements)} elements via generic selector: {selector}")
                            return valid_elements
                except:
                    continue
        except Exception as e:
            print(f"[{get_timestamp()}] Error in generic detection: {str(e)}")
        return []
    
    def _get_product_container(self, price_element) -> Any:
        """Get a reasonable product container for a price element."""
        try:
            # Try parent, then grandparent
            parent = price_element.find_element(By.XPATH, "..")
            if self._element_looks_like_product(parent):
                return parent
            
            grandparent = parent.find_element(By.XPATH, "..")
            if self._element_looks_like_product(grandparent):
                return grandparent
            
            return parent  # Fallback to parent
        except:
            return price_element
    
    def _element_looks_like_product(self, element) -> bool:
        """Check if element looks like a product container."""
        try:
            # Check if element has reasonable size and contains link or text
            size = element.size
            if size['width'] < 50 or size['height'] < 50:
                return False
            
            # Check if it contains a link
            links = element.find_elements(By.TAG_NAME, "a")
            if links:
                return True
            
            # Check if it has meaningful text
            text = element.text.strip()
            if len(text) > 10:
                return True
                
            return False
        except:
            return False
    
    def _element_has_content(self, element) -> bool:
        """Check if element has meaningful content."""
        try:
            # Check for links
            links = element.find_elements(By.TAG_NAME, "a")
            if links:
                return True
            
            # Check for images
            images = element.find_elements(By.TAG_NAME, "img")
            if images:
                return True
            
            # Check for text content
            text = element.text.strip()
            if len(text) > 5:
                return True
                
            return False
        except:
            return False
    
    def _debug_page_structure(self):
        """Debug the page structure to understand what elements are available."""
        try:
            print(f"[{get_timestamp()}] Debugging page structure...")
            
            # Get page title
            title = self.driver.title
            print(f"[{get_timestamp()}] Page title: {title}")
            
            # Check common container elements
            containers = ['div', 'section', 'article', 'main', 'ul', 'li']
            for container in containers:
                elements = self.driver.find_elements(By.TAG_NAME, container)
                if len(elements) > 10:
                    print(f"[{get_timestamp()}] Found {len(elements)} {container} elements")
            
            # Check for elements with common class patterns
            class_patterns = ['product', 'item', 'card', 'grid', 'list']
            for pattern in class_patterns:
                elements = self.driver.find_elements(By.CSS_SELECTOR, f"[class*='{pattern}']")
                if elements:
                    print(f"[{get_timestamp()}] Found {len(elements)} elements with class containing '{pattern}'")
            
            # Check for links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            print(f"[{get_timestamp()}] Found {len(links)} links on page")
            
            # Sample some class names to help understand the structure
            divs = self.driver.find_elements(By.TAG_NAME, "div")[:20]
            class_names = []
            for div in divs:
                class_attr = div.get_attribute("class")
                if class_attr:
                    class_names.extend(class_attr.split())
            
            unique_classes = list(set(class_names))[:10]
            if unique_classes:
                print(f"[{get_timestamp()}] Sample class names: {', '.join(unique_classes)}")
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error in debug: {str(e)}")
    
    def extract_product_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract product information from an ETB product element."""
        if not element:
            return None
        
        try:
            product = {
                'name': self._extract_title(element),
                'price': self._extract_price(element),
                'priceShow': '',
                'image': self._extract_image_url(element),
                'url': self._extract_product_url(element),
                'inStock': True,  # Default to in stock for ETB
                'source': 'ETB International',
                'extracted_at': get_timestamp()
            }
            
            # Set priceShow from price if available
            if product['price']:
                product['priceShow'] = str(product['price'])
            
            # Only return products with at least a name
            if product['name']:
                return product
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error extracting product info: {str(e)}")
        
        return None
    
    def _extract_title(self, element) -> str:
        """Extract product title from ETB element."""
        for selector in self.ETB_TITLE_SELECTORS:
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.get_attribute('title') or title_elem.text.strip()
                if title and len(title.strip()) > 0:
                    return title.strip()
            except:
                continue
        
        # Fallback: try to get text from the element itself or its first link
        try:
            # Try element's own text
            element_text = element.text.strip()
            if element_text and len(element_text) > 0 and len(element_text) < 200:
                return element_text
            
            # Try first link's text
            first_link = element.find_element(By.TAG_NAME, "a")
            link_text = first_link.text.strip()
            if link_text and len(link_text) > 0:
                return link_text
        except:
            pass
        
        return ""
    
    def _extract_price(self, element) -> Optional[float]:
        """Extract product price from ETB element."""
        for selector in self.ETB_PRICE_SELECTORS:
            try:
                price_elem = element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text.strip() or price_elem.get_attribute('data-price') or price_elem.get_attribute('content')
                if price_text:
                    # Extract numeric value from price text
                    import re
                    numbers = re.findall(r'[\d.,]+', price_text.replace(',', ''))
                    if numbers:
                        try:
                            return float(numbers[0].replace(',', ''))
                        except ValueError:
                            continue
            except:
                continue
        return None
    
    def _extract_image_url(self, element) -> str:
        """Extract product image URL from ETB element."""
        for selector in self.ETB_IMAGE_SELECTORS:
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, selector)
                img_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
                if img_url:
                    # Handle relative URLs
                    if img_url.startswith('//'):
                        return 'https:' + img_url
                    elif img_url.startswith('/'):
                        current_url = self.driver.current_url
                        from urllib.parse import urlparse
                        parsed = urlparse(current_url)
                        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
                    elif img_url.startswith('http'):
                        return img_url
            except:
                continue
        return ""
    
    def _extract_product_url(self, element) -> str:
        """Extract product URL from ETB element."""
        try:
            # Try to find link within the element
            for selector in self.ETB_LINK_SELECTORS:
                try:
                    link_elem = element.find_element(By.CSS_SELECTOR, selector)
                    href = link_elem.get_attribute('href')
                    if href and href != '#':
                        return self._normalize_url(href)
                except:
                    continue
            
            # Try to find any link within the element
            try:
                links = element.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and href != '#' and not href.startswith('javascript:'):
                        return self._normalize_url(href)
            except:
                pass
            
            # If element itself is a link
            try:
                href = element.get_attribute('href')
                if href and href != '#':
                    return self._normalize_url(href)
            except:
                pass
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error extracting product URL: {str(e)}")
        
        return ""
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to be absolute."""
        try:
            if url.startswith('http') or url.startswith('file://'):
                return url
            elif url.startswith('//'):
                return 'https:' + url
            elif url.startswith('/'):
                current_url = self.driver.current_url
                from urllib.parse import urlparse
                parsed = urlparse(current_url)
                return f"{parsed.scheme}://{parsed.netloc}{url}"
            else:
                # Relative URL - use urljoin for proper handling
                from urllib.parse import urljoin
                current_url = self.driver.current_url
                return urljoin(current_url, url)
        except:
            return url


class InternationalETBScraper:
    """Custom scraper for international ETB e-commerce sites."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('SCRAPING_URL_INTL_ETB')
        self.webdriver_manager = ETBWebDriverManager()
        self.product_extractor = None
        
        if not self.base_url:
            print(f"[{get_timestamp()}] Warning: SCRAPING_URL_INTL_ETB environment variable not set")
    
    def scrape_products(self) -> List[Dict[str, Any]]:
        """Main scraping flow for ETB sites."""
        if not self.base_url:
            print(f"[{get_timestamp()}] No URL provided for scraping")
            return []
        
        try:
            print(f"[{get_timestamp()}] Starting ETB scraper for: {self.base_url}")
            
            # Setup driver
            if not self.webdriver_manager.setup_driver():
                print(f"[{get_timestamp()}] Failed to setup browser driver for ETB scraping.")
                return []
            
            self.product_extractor = ETBProductExtractor(self.webdriver_manager.driver)
            
            # Navigate to the page
            print(f"[{get_timestamp()}] Navigating to ETB page...")
            self.webdriver_manager.driver.get(self.base_url)
            
            # Wait for page to load completely
            print(f"[{get_timestamp()}] Waiting for page to load completely...")
            time.sleep(5)
            
            # Check if page loaded successfully
            current_url = self.webdriver_manager.driver.current_url
            page_title = self.webdriver_manager.driver.title
            print(f"[{get_timestamp()}] Page loaded - URL: {current_url}, Title: {page_title}")
            
            # Wait for products to load
            product_elements = self.product_extractor.wait_for_products_to_load(timeout=30)
            
            if not product_elements:
                print(f"[{get_timestamp()}] No products found on ETB page")
                return []
            
            # Extract product information
            products = []
            print(f"[{get_timestamp()}] Extracting information from {len(product_elements)} ETB products...")
            
            for idx, element in enumerate(product_elements):
                try:
                    product = self.product_extractor.extract_product_info(element)
                    if product:
                        products.append(product)
                        if len(products) % 10 == 0:  # Progress indicator
                            print(f"[{get_timestamp()}] Processed {len(products)} products...")
                except Exception as e:
                    print(f"[{get_timestamp()}] Error processing product {idx}: {str(e)}")
                    continue
            
            print(f"[{get_timestamp()}] ETB scraping completed. Found {len(products)} products.")
            return products
            
        except Exception as e:
            print(f"[{get_timestamp()}] ETB scraper error: {str(e)}")
            return []
        finally:
            self.webdriver_manager.quit_driver()


def main():
    """Main entry point for international ETB scraper."""
    print(f"[{get_timestamp()}] International ETB Scraper starting...")
    
    # Check if SCRAPING_URL_INTL_ETB is set
    intl_url = os.getenv('SCRAPING_URL_INTL_ETB')
    if not intl_url:
        print(f"[{get_timestamp()}] Error: SCRAPING_URL_INTL_ETB environment variable not set")
        print(f"[{get_timestamp()}] Please set the SCRAPING_URL_INTL_ETB environment variable and try again")
        return
    
    print(f"[{get_timestamp()}] Using international ETB URL: {intl_url}")
    
    # Initialize custom ETB scraper
    etb_scraper = InternationalETBScraper(intl_url)
    all_products = etb_scraper.scrape_products()

    # For ETB sites, we assume all found products are available
    available_products = all_products
    
    # Log results
    print(f"[{get_timestamp()}] ETB scraping completed:")
    print(f"[{get_timestamp()}] - Total products found: {len(all_products)}")
    print(f"[{get_timestamp()}] - Available products: {len(available_products)}")

    # Try to send notifications if notification_service module exists
    try:
        from notification_service import create_notification_service
        notification_service = create_notification_service()
        if available_products:
            print(f"[{get_timestamp()}] Sending notifications for {len(available_products)} ETB products")
            success = notification_service.notify_products(available_products)
            if success:
                print(f"[{get_timestamp()}] ETB product notifications sent successfully")
            else:
                print(f"[{get_timestamp()}] Failed to send ETB product notifications")
        else:
            print(f"[{get_timestamp()}] No available ETB products found - no notifications sent")
    except ImportError:
        print(f"[{get_timestamp()}] Notification service not available - running without notifications")
    except Exception as e:
        print(f"[{get_timestamp()}] Error in notification service: {str(e)}")

    # Save results to JSON if any available products found
    if available_products:
        print(f"[{get_timestamp()}] Saving ETB products to file...")
        filename = f"available_products_etb_intl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(available_products, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] ETB products saved to {filename}")
            
            # Also save a summary
            summary = {
                'scrape_time': get_timestamp(),
                'url_scraped': intl_url,
                'total_products': len(all_products),
                'available_products': len(available_products),
                'scraper_type': 'ETB International Custom',
                'products': available_products
            }
            
            summary_filename = f"etb_scrape_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"[{get_timestamp()}] ETB scrape summary saved to {summary_filename}")
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error saving ETB results: {str(e)}")
    else:
        print(f"[{get_timestamp()}] No ETB products found to save.")

    print(f"[{get_timestamp()}] International ETB scraper completed.")


if __name__ == "__main__":
    main()
