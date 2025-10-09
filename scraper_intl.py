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
import random
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

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
    
    # Realistic user agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.6931.134 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0'
    ]
    
    def __init__(self):
        self.driver = None
        self.current_user_agent = random.choice(self.USER_AGENTS)
        
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
        """Configure Chrome options specifically for ETB sites with enhanced anti-bot protection."""
        chrome_options = Options()
        
        # Basic Chrome options
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        # Randomize window size to look more natural
        window_sizes = ['1920,1080', '1366,768', '1536,864', '1440,900', '1600,900']
        selected_size = random.choice(window_sizes)
        chrome_options.add_argument(f'--window-size={selected_size}')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        
        # Enhanced anti-detection measures for Incapsula
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Rotate user agent to avoid detection
        chrome_options.add_argument(f'--user-agent={self.current_user_agent}')
        
        # Additional anti-bot protection evasion for multiple systems
        chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-field-trial-config')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # Enhanced stealth measures
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-hang-monitor')
        chrome_options.add_argument('--disable-prompt-on-repost')
        chrome_options.add_argument('--disable-domain-reliability')
        chrome_options.add_argument('--disable-component-update')
        
        # More natural browser behavior
        chrome_options.add_argument('--enable-features=NetworkService')
        chrome_options.add_argument('--force-device-scale-factor=1')
        chrome_options.add_argument('--simulate-outdated-no-au="Tue, 31 Dec 2099 23:59:59 GMT"')
        
        # Enhanced prefs to make browser appear more natural
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2
            },
            "profile.managed_default_content_settings": {
                "images": 2
            },
            "profile.content_settings": {
                "pattern_pairs": {}
            },
            "credentials_enable_service": False,
            "password_manager_enabled": False,
            "webrtc.ip_handling_policy": "disable_non_proxied_udp"
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        return chrome_options
    
    def _try_system_chromedriver(self, chrome_options: Options) -> bool:
        """Try to setup driver with system chromedriver."""
        try:
            # Try different chromedriver paths
            chromedriver_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver']
            
            for path in chromedriver_paths:
                try:
                    service = Service(path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self._apply_anti_detection_measures()
                    return True
                except Exception:
                    continue
                    
            # If no system chromedriver found, let webdriver-manager handle it
            return False
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
            self._apply_anti_detection_measures()
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to setup Chrome driver with webdriver manager: {str(e)}")
            return False
    
    def _apply_anti_detection_measures(self):
        """Apply comprehensive anti-detection measures to the driver."""
        try:
            # Comprehensive navigator property overrides for Incapsula evasion
            self.driver.execute_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins array to look realistic
                Object.defineProperty(navigator, 'plugins', {
                    get: () => ({
                        0: {
                            name: "Chrome PDF Plugin",
                            filename: "internal-pdf-viewer",
                            description: "Portable Document Format"
                        },
                        1: {
                            name: "Chrome PDF Viewer",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            description: ""
                        },
                        2: {
                            name: "Native Client",
                            filename: "internal-nacl-plugin",
                            description: ""
                        },
                        length: 3
                    })
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Set realistic platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Set realistic hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
                
                // Set realistic device memory
                if ('deviceMemory' in navigator) {
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8
                    });
                }
            """)
            
            # Set realistic chrome runtime and window properties
            self.driver.execute_script("""
                window.chrome = {
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'disabled',
                            INSTALLED: 'installed',
                            NOT_INSTALLED: 'not_installed'
                        },
                        RunningState: {
                            CANNOT_RUN: 'cannot_run',
                            READY_TO_RUN: 'ready_to_run',
                            RUNNING: 'running'
                        }
                    },
                    runtime: {
                        onConnect: null,
                        onMessage: null
                    }
                };
                
                // Override screen properties
                Object.defineProperty(screen, 'availTop', {get: () => 0});
                Object.defineProperty(screen, 'availLeft', {get: () => 0});
                Object.defineProperty(screen, 'availHeight', {get: () => 1040});
                Object.defineProperty(screen, 'availWidth', {get: () => 1920});
                Object.defineProperty(screen, 'colorDepth', {get: () => 24});
                Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
            """)
            
            # Enhanced permissions API override
            self.driver.execute_script("""
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: 'default', onchange: null });
                    }
                    if (parameters.name === 'geolocation') {
                        return Promise.resolve({ state: 'prompt', onchange: null });
                    }
                    return originalQuery ? originalQuery(parameters) : Promise.resolve({ state: 'granted' });
                };
                
                // Override getTimezoneOffset to look realistic
                Date.prototype.getTimezoneOffset = function() {
                    return 300; // EST timezone
                };
                
                // Mock battery API if available
                if ('getBattery' in navigator) {
                    navigator.getBattery = () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1,
                        addEventListener: () => {},
                        removeEventListener: () => {},
                        dispatchEvent: () => {}
                    });
                }
            """)
            
            # Additional measures for better stealth
            self.driver.execute_script("""
                // Override automation-related properties
                if ('automation' in window) {
                    delete window.automation;
                }
                
                // Mock realistic WebGL parameters
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel(R) HD Graphics 620';
                    }
                    return getParameter(parameter);
                };
                
                // Override toString methods to hide automation
                const originalToString = Function.prototype.toString;
                Function.prototype.toString = function() {
                    if (this === navigator.webdriver) {
                        return 'undefined';
                    }
                    return originalToString.call(this);
                };
            """)
            
            # Add realistic request headers using CDP (Chrome DevTools Protocol)
            try:
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": self.current_user_agent,
                    "acceptLanguage": "en-US,en;q=0.9",
                    "platform": "Win32"
                })
                
                # Enable network domain for header manipulation
                self.driver.execute_cdp_cmd('Network.enable', {})
                
                print(f"[{get_timestamp()}] Applied realistic request headers via CDP")
                
            except Exception as cdp_error:
                print(f"[{get_timestamp()}] Could not apply CDP headers: {str(cdp_error)}")
            
        except Exception as e:
            print(f"[{get_timestamp()}] Warning: Could not apply all anti-detection measures: {str(e)}")

    def is_blocked_by_protection(self, page_source: str, page_title: str) -> Tuple[bool, str]:
        """Check if the page is blocked by anti-bot protection systems."""
        page_source_lower = page_source.lower()
        page_title_lower = page_title.lower() if page_title else ""
        
        # Enhanced Incapsula detection
        incapsula_indicators = [
            "incapsula incident id",
            "_incap_sys_visid_",
            "incapsula",
            "visid_incap_",
            "__incap"
        ]
        for indicator in incapsula_indicators:
            if indicator in page_source_lower:
                return True, "Incapsula"
        
        # Enhanced Cloudflare detection
        cloudflare_indicators = [
            "cloudflare ray id",
            "checking your browser",
            "please enable cookies",
            "ddos protection by cloudflare",
            "attention required! | cloudflare",
            "cf-ray:",
            "__cf_bm",
            "cf_clearance",
            "cloudflare",
            "just a moment"
        ]
        for indicator in cloudflare_indicators:
            if indicator in page_source_lower or indicator in page_title_lower:
                return True, "Cloudflare"
        
        # DataDome detection
        datadome_indicators = [
            "datadome",
            "dd_captcha",
            "_dd_s",
            "geo.captcha-delivery.com"
        ]
        for indicator in datadome_indicators:
            if indicator in page_source_lower:
                return True, "DataDome"
        
        # PerimeterX detection
        perimeterx_indicators = [
            "_px",
            "perimeterx",
            "px-captcha",
            "_pxhd"
        ]
        for indicator in perimeterx_indicators:
            if indicator in page_source_lower:
                return True, "PerimeterX"
        
        # Generic bot detection
        bot_indicators = [
            "access denied",
            "blocked by security",
            "suspicious activity",
            "rate limit exceeded",
            "temporarily unavailable",
            "security check",
            "human verification",
            "robot or human",
            "verify you are human",
            "captcha",
            "too many requests"
        ]
        for indicator in bot_indicators:
            if indicator in page_source_lower or indicator in page_title_lower:
                return True, "Generic Anti-bot"
        
        return False, ""

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
            print(f"[{get_timestamp()}] === FALLBACK PRODUCT DETECTION ===")
            
            # Strategy 1: Find elements by price selectors and get their containers
            print(f"[{get_timestamp()}] Strategy 1: Price-based detection...")
            price_elements = self._find_elements_by_price()
            if price_elements:
                print(f"[{get_timestamp()}] Success: Found {len(price_elements)} products via price detection")
                return price_elements
            
            # Strategy 2: Find elements containing common e-commerce patterns
            print(f"[{get_timestamp()}] Strategy 2: Pattern-based detection...")
            pattern_elements = self._find_elements_by_patterns()
            if pattern_elements:
                print(f"[{get_timestamp()}] Success: Found {len(pattern_elements)} products via pattern detection")
                return pattern_elements
            
            # Strategy 3: Enhanced generic container detection
            print(f"[{get_timestamp()}] Strategy 3: Generic container detection...")
            generic_elements = self._find_generic_containers()
            if generic_elements:
                print(f"[{get_timestamp()}] Success: Found {len(generic_elements)} products via generic detection")
                return generic_elements
            
            # Strategy 4: Advanced DOM analysis
            print(f"[{get_timestamp()}] Strategy 4: Advanced DOM analysis...")
            advanced_elements = self._advanced_dom_analysis()
            if advanced_elements:
                print(f"[{get_timestamp()}] Success: Found {len(advanced_elements)} products via DOM analysis")
                return advanced_elements
            
            # Strategy 5: Debug page structure to understand what we're working with
            print(f"[{get_timestamp()}] Strategy 5: Comprehensive page analysis...")
            self._debug_page_structure()
            
            # Strategy 6: Try dynamic content detection (for SPAs)
            print(f"[{get_timestamp()}] Strategy 6: Dynamic content detection...")
            dynamic_elements = self._find_dynamic_content()
            if dynamic_elements:
                print(f"[{get_timestamp()}] Success: Found {len(dynamic_elements)} products via dynamic detection")
                return dynamic_elements
            
            print(f"[{get_timestamp()}] All fallback strategies exhausted - no products found")
            return []
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in fallback detection: {str(e)}")
            import traceback
            print(f"[{get_timestamp()}] Fallback detection traceback: {traceback.format_exc()}")
            return []
    
    def _find_elements_by_price(self) -> List[Any]:
        """Find product containers by looking for price elements."""
        try:
            print(f"[{get_timestamp()}] Trying price-based product detection...")
            all_containers = []
            
            for i, price_selector in enumerate(self.ETB_PRICE_SELECTORS[:10]):  # Try first 10 price selectors
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, price_selector)
                    print(f"[{get_timestamp()}] Price selector {i+1}/10 '{price_selector}' -> {len(price_elements)} elements")
                    
                    if price_elements:
                        # Sample some price text to validate
                        sample_texts = []
                        for elem in price_elements[:3]:
                            try:
                                text = elem.text.strip() or elem.get_attribute('textContent') or ''
                                if text:
                                    sample_texts.append(text[:50])
                            except:
                                pass
                        
                        if sample_texts:
                            print(f"[{get_timestamp()}] Sample price texts: {sample_texts}")
                        
                        # Get parent containers of price elements
                        containers = []
                        for price_elem in price_elements[:30]:  # Increased limit
                            try:
                                # Try to get a reasonable container (parent or grandparent)
                                container = self._get_product_container(price_elem)
                                if container and container not in containers:
                                    containers.append(container)
                            except:
                                continue
                        
                        if containers:
                            print(f"[{get_timestamp()}] Price selector '{price_selector}' yielded {len(containers)} containers")
                            all_containers.extend(containers)
                            
                except Exception as e:
                    print(f"[{get_timestamp()}] Error with price selector '{price_selector}': {str(e)}")
                    continue
            
            # Remove duplicates and return
            unique_containers = []
            for container in all_containers:
                if container not in unique_containers:
                    unique_containers.append(container)
            
            if unique_containers:
                print(f"[{get_timestamp()}] Total unique containers from price detection: {len(unique_containers)}")
                return unique_containers
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in price-based detection: {str(e)}")
        
        print(f"[{get_timestamp()}] No products found via price detection")
        return []
    
    def _find_elements_by_patterns(self) -> List[Any]:
        """Find elements that contain common e-commerce patterns."""
        try:
            print(f"[{get_timestamp()}] Trying pattern-based product detection...")
            all_containers = []
            
            # Strategy 1: Find product links and their containers
            try:
                links = self.driver.find_elements(By.TAG_NAME, "a")
                print(f"[{get_timestamp()}] Analyzing {len(links)} links for product patterns...")
                
                product_links = []
                sample_hrefs = []
                
                for link in links[:100]:  # Sample first 100 links
                    href = link.get_attribute('href')
                    if href:
                        sample_hrefs.append(href)
                        if self._href_looks_like_product(href):
                            product_links.append(link)
                
                print(f"[{get_timestamp()}] Sample hrefs: {sample_hrefs[:5]}")
                print(f"[{get_timestamp()}] Found {len(product_links)} product-like links")
                
                if len(product_links) >= 2:
                    containers = []
                    for link in product_links:
                        try:
                            # Try different levels of parent containers
                            parent = link.find_element(By.XPATH, "..")
                            grandparent = parent.find_element(By.XPATH, "..")
                            
                            # Choose the more likely container
                            container = grandparent if self._element_looks_like_product(grandparent) else parent
                            
                            if container and container not in containers:
                                containers.append(container)
                        except:
                            if link not in containers:
                                containers.append(link)
                    
                    if len(containers) >= 2:
                        print(f"[{get_timestamp()}] Product link strategy: {len(containers)} containers")
                        all_containers.extend(containers)
            except Exception as e:
                print(f"[{get_timestamp()}] Error in link analysis: {str(e)}")
            
            # Strategy 2: CSS selector patterns
            patterns = [
                ("div:has(a[href])", "Divs with links"),
                ("article", "Article elements"),
                ("li:has(a)", "List items with links"),
                ("[class*='item']:has(a)", "Item classes with links"),
                ("[class*='card']:has(a)", "Card classes with links"),
                ("[class*='product']", "Product classes"),
                ("div[data-testid]", "Test ID divs"),
                ("section > div", "Section subdivisions")
            ]
            
            for pattern, description in patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    print(f"[{get_timestamp()}] Pattern '{pattern}' ({description}): {len(elements)} elements")
                    
                    if elements and len(elements) >= 2:
                        # Filter elements that look like products
                        product_like = []
                        for elem in elements[:50]:  # Limit for performance
                            if self._element_looks_like_product(elem):
                                product_like.append(elem)
                        
                        if len(product_like) >= 2:
                            print(f"[{get_timestamp()}] Pattern '{pattern}': {len(product_like)} product-like elements")
                            all_containers.extend(product_like)
                        
                except Exception as e:
                    print(f"[{get_timestamp()}] Error with pattern '{pattern}': {str(e)}")
                    continue
            
            # Remove duplicates and return best candidates
            unique_containers = []
            for container in all_containers:
                if container not in unique_containers:
                    unique_containers.append(container)
            
            if unique_containers:
                print(f"[{get_timestamp()}] Total unique containers from pattern detection: {len(unique_containers)}")
                return unique_containers[:50]  # Return top 50
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in pattern-based detection: {str(e)}")
        
        print(f"[{get_timestamp()}] No products found via pattern detection")
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
            all_candidates = []
            
            # Look for repetitive structures (common in product listings)
            selectors = [
                ("div > div > div", "Triple nested divs"),
                ("ul > li", "List items"),
                ("div[class]", "Divs with classes"),
                ("section > div", "Section subdivisions"),
                ("div > div", "Double nested divs"),
                ("main > div", "Main subdivisions"),
                ("div[id] > div", "ID divs with children")
            ]
            
            for selector, description in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"[{get_timestamp()}] Generic selector '{selector}' ({description}): {len(elements)} elements")
                    
                    if len(elements) > 5:  # Must be multiple similar elements
                        # Take a sample and check content quality
                        sample = elements[:30]
                        valid_elements = []
                        content_samples = []
                        
                        for elem in sample:
                            if self._element_has_content(elem):
                                valid_elements.append(elem)
                                # Sample some content for analysis
                                try:
                                    elem_text = elem.text.strip()[:100]
                                    if elem_text:
                                        content_samples.append(elem_text)
                                except:
                                    pass
                        
                        if len(valid_elements) > 3:
                            print(f"[{get_timestamp()}] Selector '{selector}': {len(valid_elements)} valid elements")
                            if content_samples:
                                print(f"[{get_timestamp()}] Sample content: {content_samples[:2]}")
                            all_candidates.extend(valid_elements)
                            
                except Exception as e:
                    print(f"[{get_timestamp()}] Error with selector '{selector}': {str(e)}")
                    continue
            
            # If we found candidates, filter for the most product-like ones
            if all_candidates:
                # Score elements and take the best ones
                scored_elements = []
                for elem in all_candidates:
                    score = self._score_element_as_product(elem)
                    if score > 0:
                        scored_elements.append((elem, score))
                
                # Sort by score and take top elements
                scored_elements.sort(key=lambda x: x[1], reverse=True)
                top_elements = [elem for elem, score in scored_elements[:20]]
                
                if top_elements:
                    print(f"[{get_timestamp()}] Generic detection: {len(top_elements)} top-scored elements")
                    return top_elements
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in generic container detection: {str(e)}")
        
        print(f"[{get_timestamp()}] No products found via generic detection")
        return []

    def _score_element_as_product(self, element) -> int:
        """Score an element based on how likely it is to be a product."""
        try:
            score = 0
            
            # Basic content check
            if not self._element_has_content(element):
                return 0
            
            # Check for images
            images = element.find_elements(By.TAG_NAME, "img")
            if images:
                score += 2
                # Bonus for multiple images
                if len(images) > 1:
                    score += 1
            
            # Check for links
            links = element.find_elements(By.TAG_NAME, "a")
            if links:
                score += 1
                # Check if links look like product links
                for link in links[:3]:
                    href = link.get_attribute('href')
                    if href and self._href_looks_like_product(href):
                        score += 2
                        break
            
            # Check text content for product indicators
            text = element.text.lower()
            
            # Price indicators
            price_indicators = ['$', '€', '£', 'usd', 'eur', 'price', 'cost', '.99', '.95']
            if any(indicator in text for indicator in price_indicators):
                score += 3
            
            # Product type indicators  
            product_indicators = ['box', 'pack', 'card', 'game', 'toy', 'collectible']
            if any(indicator in text for indicator in product_indicators):
                score += 2
            
            # Action indicators
            action_indicators = ['buy', 'add', 'cart', 'purchase', 'shop']
            if any(indicator in text for indicator in action_indicators):
                score += 1
            
            # Check CSS classes and IDs
            class_attr = element.get_attribute('class') or ''
            id_attr = element.get_attribute('id') or ''
            attrs = (class_attr + ' ' + id_attr).lower()
            
            if any(term in attrs for term in ['product', 'item', 'card', 'listing']):
                score += 3
            
            # Size check - products should have reasonable size
            try:
                size = element.size
                if size['width'] > 100 and size['height'] > 100:
                    score += 1
                if size['width'] < 50 or size['height'] < 50:
                    score -= 2
            except:
                pass
            
            return max(0, score)
            
        except:
            return 0
    
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
            print(f"[{get_timestamp()}] === ENHANCED PAGE STRUCTURE DEBUG ===")
            
            # Basic page information
            title = self.driver.title
            url = self.driver.current_url
            page_source_length = len(self.driver.page_source)
            
            print(f"[{get_timestamp()}] Page title: '{title}'")
            print(f"[{get_timestamp()}] Page URL: {url}")
            print(f"[{get_timestamp()}] Page source length: {page_source_length} characters")
            
            # Take screenshot for debugging
            self._take_debug_screenshot()
            
            # Check for common error indicators
            self._check_page_errors()
            
            # Detailed element analysis
            print(f"[{get_timestamp()}] --- Element Count Analysis ---")
            containers = ['div', 'section', 'article', 'main', 'ul', 'li', 'span', 'p', 'h1', 'h2', 'h3', 'img', 'button']
            element_counts = {}
            for container in containers:
                elements = self.driver.find_elements(By.TAG_NAME, container)
                element_counts[container] = len(elements)
                if len(elements) > 0:
                    print(f"[{get_timestamp()}] Found {len(elements)} {container} elements")
            
            # Check for elements with common e-commerce patterns
            print(f"[{get_timestamp()}] --- E-commerce Pattern Analysis ---")
            ecommerce_patterns = ['product', 'item', 'card', 'grid', 'list', 'shop', 'buy', 'price', 'cart', 'add']
            pattern_counts = {}
            for pattern in ecommerce_patterns:
                elements = self.driver.find_elements(By.CSS_SELECTOR, f"[class*='{pattern}']")
                pattern_counts[pattern] = len(elements)
                if elements:
                    print(f"[{get_timestamp()}] Found {len(elements)} elements with class containing '{pattern}'")
            
            # Analyze links
            print(f"[{get_timestamp()}] --- Link Analysis ---")
            links = self.driver.find_elements(By.TAG_NAME, "a")
            print(f"[{get_timestamp()}] Total links found: {len(links)}")
            
            # Sample and categorize links
            product_like_links = []
            external_links = []
            internal_links = []
            
            for link in links[:50]:  # Sample first 50 links
                href = link.get_attribute('href')
                if href:
                    if self._href_looks_like_product(href):
                        product_like_links.append(href)
                    elif href.startswith('http') and url.split('/')[2] not in href:
                        external_links.append(href)
                    else:
                        internal_links.append(href)
            
            print(f"[{get_timestamp()}] Product-like links: {len(product_like_links)}")
            print(f"[{get_timestamp()}] External links: {len(external_links)}")
            print(f"[{get_timestamp()}] Internal links: {len(internal_links)}")
            
            # Show sample product-like links
            if product_like_links:
                print(f"[{get_timestamp()}] Sample product links:")
                for i, link in enumerate(product_like_links[:5]):
                    print(f"[{get_timestamp()}]   {i+1}. {link}")
            
            # Advanced class and ID analysis
            print(f"[{get_timestamp()}] --- CSS Class & ID Analysis ---")
            self._analyze_css_classes_and_ids()
            
            # Test current selectors
            print(f"[{get_timestamp()}] --- Selector Testing ---")
            self._test_current_selectors()
            
            # HTML structure sampling
            print(f"[{get_timestamp()}] --- HTML Structure Sampling ---")
            self._sample_html_structure()
            
            # Page content analysis
            print(f"[{get_timestamp()}] --- Content Analysis ---")
            self._analyze_page_content()
            
            print(f"[{get_timestamp()}] === END DEBUG ANALYSIS ===")
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error in enhanced debug: {str(e)}")
            import traceback
            print(f"[{get_timestamp()}] Debug traceback: {traceback.format_exc()}")

    def _take_debug_screenshot(self):
        """Take a screenshot for debugging purposes."""
        try:
            import os
            screenshot_dir = "/tmp/debug_screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f"{screenshot_dir}/debug_page_{timestamp}.png"
            
            self.driver.save_screenshot(screenshot_path)
            print(f"[{get_timestamp()}] Debug screenshot saved: {screenshot_path}")
            
            # Also save page source for analysis
            page_source_path = f"{screenshot_dir}/debug_page_source_{timestamp}.html"
            with open(page_source_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"[{get_timestamp()}] Page source saved: {page_source_path}")
            
        except Exception as e:
            print(f"[{get_timestamp()}] Could not save debug screenshot: {str(e)}")

    def _check_page_errors(self):
        """Check for common page loading errors."""
        try:
            page_source = self.driver.page_source.lower()
            
            # Check for common error indicators
            error_indicators = [
                'error 404', '404 not found', 'page not found',
                'error 403', '403 forbidden', 'access denied',
                'error 500', '500 internal server error',
                'cloudflare', 'bot protection', 'rate limit',
                'captcha', 'security check', 'blocked'
            ]
            
            found_errors = []
            for indicator in error_indicators:
                if indicator in page_source:
                    found_errors.append(indicator)
            
            if found_errors:
                print(f"[{get_timestamp()}] WARNING: Potential page errors detected: {found_errors}")
            else:
                print(f"[{get_timestamp()}] No obvious page errors detected")
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error checking page errors: {str(e)}")

    def _analyze_css_classes_and_ids(self):
        """Analyze CSS classes and IDs to understand page structure."""
        try:
            # Collect all unique class names
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[class]")[:100]  # Sample first 100
            class_names = set()
            
            for elem in all_elements:
                class_attr = elem.get_attribute("class")
                if class_attr:
                    class_names.update(class_attr.split())
            
            # Filter and categorize classes
            product_classes = [cls for cls in class_names if any(keyword in cls.lower() 
                              for keyword in ['product', 'item', 'card', 'listing', 'grid'])]
            price_classes = [cls for cls in class_names if any(keyword in cls.lower() 
                            for keyword in ['price', 'cost', 'amount', 'currency'])]
            
            print(f"[{get_timestamp()}] Total unique CSS classes found: {len(class_names)}")
            
            if product_classes:
                print(f"[{get_timestamp()}] Product-related classes: {product_classes[:10]}")
            if price_classes:
                print(f"[{get_timestamp()}] Price-related classes: {price_classes[:10]}")
            
            # Sample some interesting class names
            interesting_classes = [cls for cls in class_names if len(cls) > 5 and '-' in cls][:15]
            if interesting_classes:
                print(f"[{get_timestamp()}] Sample complex class names: {interesting_classes}")
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error analyzing CSS classes: {str(e)}")

    def _test_current_selectors(self):
        """Test all current selectors to see what they find."""
        try:
            print(f"[{get_timestamp()}] Testing ETB product selectors:")
            for i, selector in enumerate(self.ETB_PRODUCT_SELECTORS):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> {len(elements)} elements")
                except Exception as e:
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> ERROR: {str(e)}")
            
            print(f"[{get_timestamp()}] Testing ETB price selectors:")
            for i, selector in enumerate(self.ETB_PRICE_SELECTORS[:10]):  # Test first 10
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> {len(elements)} elements")
                except Exception as e:
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> ERROR: {str(e)}")
                    
            print(f"[{get_timestamp()}] Testing ETB title selectors:")
            for i, selector in enumerate(self.ETB_TITLE_SELECTORS[:10]):  # Test first 10
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> {len(elements)} elements")
                except Exception as e:
                    print(f"[{get_timestamp()}]   {i+1}. '{selector}' -> ERROR: {str(e)}")
                    
        except Exception as e:
            print(f"[{get_timestamp()}] Error testing selectors: {str(e)}")

    def _sample_html_structure(self):
        """Sample and analyze the HTML structure."""
        try:
            # Get page source
            page_source = self.driver.page_source
            
            # Extract and show meta information
            import re
            
            # Find meta tags
            meta_tags = re.findall(r'<meta[^>]*>', page_source, re.IGNORECASE)
            print(f"[{get_timestamp()}] Found {len(meta_tags)} meta tags")
            
            # Look for script tags (might indicate SPA)
            script_tags = re.findall(r'<script[^>]*>', page_source, re.IGNORECASE)
            print(f"[{get_timestamp()}] Found {len(script_tags)} script tags")
            
            # Check if it's a Single Page Application
            spa_indicators = ['react', 'vue', 'angular', 'spa', 'app.js', 'bundle.js']
            found_spa = any(indicator in page_source.lower() for indicator in spa_indicators)
            print(f"[{get_timestamp()}] Potential SPA detected: {found_spa}")
            
            # Sample some actual HTML content
            body_match = re.search(r'<body[^>]*>(.*?)</body>', page_source, re.DOTALL | re.IGNORECASE)
            if body_match:
                body_content = body_match.group(1)
                # Get first 1000 characters of body content
                body_sample = body_content[:1000].replace('\n', ' ').replace('\t', ' ')
                # Remove extra spaces
                body_sample = re.sub(r'\s+', ' ', body_sample)
                print(f"[{get_timestamp()}] Body content sample: {body_sample}...")
            
            # Look for common e-commerce frameworks
            ecommerce_frameworks = ['shopify', 'woocommerce', 'magento', 'opencart', 'prestashop']
            found_frameworks = [fw for fw in ecommerce_frameworks if fw in page_source.lower()]
            if found_frameworks:
                print(f"[{get_timestamp()}] Detected e-commerce frameworks: {found_frameworks}")
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error sampling HTML structure: {str(e)}")

    def _analyze_page_content(self):
        """Analyze page content for product-related text."""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for product-related keywords
            product_keywords = ['elite trainer box', 'etb', 'pokemon', 'trading card', 'booster', 
                              'pack', 'card game', 'collectible', 'price', '$', 'add to cart', 'buy']
            
            found_keywords = []
            page_text_lower = page_text.lower()
            
            for keyword in product_keywords:
                if keyword in page_text_lower:
                    found_keywords.append(keyword)
            
            print(f"[{get_timestamp()}] Product-related keywords found: {found_keywords}")
            
            # Check text length and content quality
            print(f"[{get_timestamp()}] Page text length: {len(page_text)} characters")
            
            if len(page_text) < 100:
                print(f"[{get_timestamp()}] WARNING: Very little text content - page may not have loaded properly")
                print(f"[{get_timestamp()}] Page text sample: '{page_text[:200]}'")
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error analyzing page content: {str(e)}")
    
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

    def _advanced_dom_analysis(self) -> List[Any]:
        """Advanced DOM analysis to find product-like structures."""
        try:
            print(f"[{get_timestamp()}] Performing advanced DOM analysis...")
            
            # Look for repetitive structures that might be products
            containers = []
            
            # Try to find elements with similar sibling structures
            potential_containers = self.driver.find_elements(By.CSS_SELECTOR, "div, li, article, section")
            
            # Group by parent to find repetitive patterns
            parent_children = {}
            for elem in potential_containers[:200]:  # Limit for performance
                try:
                    parent = elem.find_element(By.XPATH, "..")
                    parent_tag = parent.tag_name + (parent.get_attribute('class') or '')
                    
                    if parent_tag not in parent_children:
                        parent_children[parent_tag] = []
                    parent_children[parent_tag].append(elem)
                except:
                    continue
            
            # Find parents with multiple similar children (likely product listings)
            for parent_key, children in parent_children.items():
                if len(children) >= 3:  # At least 3 similar elements
                    # Check if children have product-like characteristics
                    valid_children = []
                    for child in children[:20]:  # Sample first 20
                        if self._element_looks_like_product_advanced(child):
                            valid_children.append(child)
                    
                    if len(valid_children) >= 2:
                        print(f"[{get_timestamp()}] Found {len(valid_children)} product-like elements in container pattern: {parent_key[:50]}")
                        containers.extend(valid_children)
            
            return containers[:50]  # Return up to 50 elements
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in advanced DOM analysis: {str(e)}")
            return []

    def _element_looks_like_product_advanced(self, element) -> bool:
        """Advanced check if element looks like a product container."""
        try:
            # Check basic requirements
            if not self._element_looks_like_product(element):
                return False
            
            # Additional checks for e-commerce characteristics
            
            # Check for images (products usually have images)
            images = element.find_elements(By.TAG_NAME, "img")
            has_image = len(images) > 0
            
            # Check for price-like text patterns
            element_text = element.text.lower()
            price_patterns = ['$', '€', '£', '¥', 'usd', 'eur', 'price', 'cost']
            has_price_indicator = any(pattern in element_text for pattern in price_patterns)
            
            # Check for action words
            action_patterns = ['buy', 'add', 'cart', 'shop', 'purchase', 'order']
            has_action = any(pattern in element_text for pattern in action_patterns)
            
            # Check for product-related classes
            class_attr = element.get_attribute('class') or ''
            id_attr = element.get_attribute('id') or ''
            combined_attrs = (class_attr + ' ' + id_attr).lower()
            
            product_class_patterns = ['product', 'item', 'card', 'listing', 'shop']
            has_product_class = any(pattern in combined_attrs for pattern in product_class_patterns)
            
            # Score the element
            score = 0
            if has_image: score += 2
            if has_price_indicator: score += 3
            if has_action: score += 1
            if has_product_class: score += 2
            
            # Element is likely a product if score >= 3
            return score >= 3
            
        except:
            return False

    def _find_dynamic_content(self) -> List[Any]:
        """Try to find dynamically loaded content (for SPAs)."""
        try:
            print(f"[{get_timestamp()}] Checking for dynamic/SPA content...")
            
            # Wait a bit for dynamic content to load
            import time
            time.sleep(3)
            
            # Look for elements that might be loaded dynamically
            dynamic_selectors = [
                "[data-testid*='product']",
                "[data-cy*='product']", 
                "[data-qa*='product']",
                "[id*='product']",
                "[class*='ProductCard']",
                "[class*='ProductItem']",
                "[class*='product-card']",
                "[class*='product-item']",
                "[data-track*='product']",
                "div[data-product]",
                "div[data-item]"
            ]
            
            found_elements = []
            for selector in dynamic_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[{get_timestamp()}] Dynamic selector '{selector}' found {len(elements)} elements")
                        found_elements.extend(elements)
                except:
                    continue
            
            # Remove duplicates
            unique_elements = []
            for elem in found_elements:
                if elem not in unique_elements:
                    unique_elements.append(elem)
            
            # Try scroll-based detection (infinite scroll pages)
            if not unique_elements:
                print(f"[{get_timestamp()}] Trying scroll-based content detection...")
                initial_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                
                # Look again for content
                all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                current_count = len(all_divs)
                
                # Check if new content appeared after scrolling
                final_height = self.driver.execute_script("return document.body.scrollHeight")
                if final_height > initial_height:
                    print(f"[{get_timestamp()}] Page height changed after scroll - dynamic content detected")
                    
                    # Re-run pattern detection
                    pattern_elements = self._find_elements_by_patterns()
                    if pattern_elements:
                        unique_elements.extend(pattern_elements)
            
            return unique_elements[:30]  # Return up to 30 elements
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in dynamic content detection: {str(e)}")
            return []


class InternationalETBScraper:
    """Custom scraper for international ETB e-commerce sites."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('SCRAPING_URL_INTL_ETB')
        self.webdriver_manager = ETBWebDriverManager()
        self.product_extractor = None
        
        if not self.base_url:
            print(f"[{get_timestamp()}] Warning: SCRAPING_URL_INTL_ETB environment variable not set")
    
    def _handle_protection_retry(self, protection_type: str) -> bool:
        """Handle anti-bot protection with enhanced retry strategies."""
        print(f"[{get_timestamp()}] Attempting to bypass {protection_type} protection...")
        
        # Enhanced retry strategies specifically for Incapsula
        retry_strategies = [
            ("Progressive delay with navigation", self._retry_progressive_delay),
            ("Clear cookies and stealth reload", self._retry_clear_cookies_enhanced),
            ("Human-like browsing simulation", self._retry_human_behavior),
            ("Long wait and reload", self._retry_wait_and_reload),
            ("Random delay retry", self._retry_random_delay),
        ]
        
        for strategy_name, strategy_func in retry_strategies:
            try:
                print(f"[{get_timestamp()}] Trying strategy: {strategy_name}")
                success = strategy_func()
                if success:
                    print(f"[{get_timestamp()}] SUCCESS: {strategy_name} worked")
                    return True
                else:
                    print(f"[{get_timestamp()}] FAILED: {strategy_name} did not work")
                    # Add progressive backoff between strategies
                    time.sleep(random.uniform(2, 5))
            except Exception as e:
                print(f"[{get_timestamp()}] ERROR in {strategy_name}: {str(e)}")
                continue
        
        return False
    
    def _retry_wait_and_reload(self) -> bool:
        """Wait longer and reload the page."""
        try:
            print(f"[{get_timestamp()}] Waiting 10 seconds before reload...")
            time.sleep(10)
            self.webdriver_manager.driver.refresh()
            time.sleep(8)
            
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            return not is_blocked
        except Exception:
            return False
    
    def _retry_clear_cookies(self) -> bool:
        """Clear cookies and reload."""
        try:
            print(f"[{get_timestamp()}] Clearing cookies and reloading...")
            self.webdriver_manager.driver.delete_all_cookies()
            time.sleep(3)
            self.webdriver_manager.driver.get(self.base_url)
            time.sleep(8)
            
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            return not is_blocked
        except Exception:
            return False
    
    def _retry_random_delay(self) -> bool:
        """Wait a random delay and retry."""
        try:
            delay = random.uniform(5, 15)
            print(f"[{get_timestamp()}] Random delay of {delay:.1f} seconds...")
            time.sleep(delay)
            self.webdriver_manager.driver.refresh()
            time.sleep(5)
            
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            return not is_blocked
        except Exception:
            return False
    
    def _retry_progressive_delay(self) -> bool:
        """Wait with progressive delays and multiple reload attempts."""
        try:
            # Progressive delays: 15s, 30s, 45s
            delays = [15, 30, 45]
            
            for i, delay in enumerate(delays):
                print(f"[{get_timestamp()}] Progressive delay attempt {i+1}/3: {delay} seconds...")
                time.sleep(delay)
                
                # Clear cache and reload
                self.webdriver_manager.driver.execute_script("window.localStorage.clear();")
                self.webdriver_manager.driver.execute_script("window.sessionStorage.clear();")
                self.webdriver_manager.driver.refresh()
                time.sleep(8)
                
                page_source = self.webdriver_manager.driver.page_source
                page_title = self.webdriver_manager.driver.title
                is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
                
                if not is_blocked:
                    print(f"[{get_timestamp()}] Progressive delay succeeded after {delay}s wait")
                    return True
                
                print(f"[{get_timestamp()}] Still blocked after {delay}s wait, trying next delay...")
            
            return False
        except Exception:
            return False
    
    def _retry_clear_cookies_enhanced(self) -> bool:
        """Enhanced cookie clearing with additional cleanup."""
        try:
            print(f"[{get_timestamp()}] Enhanced cookie and cache clearing...")
            
            # Clear all browser data
            self.webdriver_manager.driver.delete_all_cookies()
            self.webdriver_manager.driver.execute_script("window.localStorage.clear();")
            self.webdriver_manager.driver.execute_script("window.sessionStorage.clear();")
            
            # Navigate to empty page first
            self.webdriver_manager.driver.get("about:blank")
            time.sleep(3)
            
            # Re-apply anti-detection measures
            self.webdriver_manager._apply_anti_detection_measures()
            time.sleep(2)
            
            # Navigate to target page
            self.webdriver_manager.driver.get(self.base_url)
            time.sleep(12)  # Longer wait after clearing everything
            
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            return not is_blocked
        except Exception:
            return False
    
    def _retry_human_behavior(self) -> bool:
        """Simulate human-like browsing behavior."""
        try:
            print(f"[{get_timestamp()}] Simulating human-like browsing behavior...")
            
            # First navigate to homepage
            from urllib.parse import urlparse
            parsed_url = urlparse(self.base_url)
            homepage_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            print(f"[{get_timestamp()}] Navigating to homepage first: {homepage_url}")
            self.webdriver_manager.driver.get(homepage_url)
            time.sleep(random.uniform(8, 12))
            
            # Simulate some scrolling
            print(f"[{get_timestamp()}] Simulating scrolling behavior...")
            for _ in range(3):
                scroll_y = random.randint(200, 800)
                self.webdriver_manager.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
                time.sleep(random.uniform(1, 3))
            
            # Scroll back to top
            self.webdriver_manager.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(2, 4))
            
            # Now navigate to target page
            print(f"[{get_timestamp()}] Navigating to target page...")
            self.webdriver_manager.driver.get(self.base_url)
            time.sleep(random.uniform(10, 15))
            
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            is_blocked, _ = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            return not is_blocked
        except Exception:
            return False
    
    def _print_protection_specific_guidance(self, protection_type: str):
        """Print specific troubleshooting guidance based on protection type."""
        print(f"[{get_timestamp()}] === {protection_type.upper()} PROTECTION BYPASS GUIDANCE ===")
        
        if protection_type == "Incapsula":
            print(f"[{get_timestamp()}] Incapsula is an advanced bot protection system.")
            print(f"[{get_timestamp()}] RECOMMENDATIONS:")
            print(f"[{get_timestamp()}] 1. Try accessing the site manually in a browser first")
            print(f"[{get_timestamp()}] 2. Use residential IP addresses (not datacenter/VPS IPs)")
            print(f"[{get_timestamp()}] 3. Implement longer delays between requests (30-60 seconds)")
            print(f"[{get_timestamp()}] 4. Consider rotating user agents and browser fingerprints")
            print(f"[{get_timestamp()}] 5. Some Incapsula sites require JavaScript challenges to be solved")
            print(f"[{get_timestamp()}] 6. Try running from different geographic locations")
            
        elif protection_type == "Cloudflare":
            print(f"[{get_timestamp()}] Cloudflare protection detected.")
            print(f"[{get_timestamp()}] RECOMMENDATIONS:")
            print(f"[{get_timestamp()}] 1. Wait for challenge page to complete automatically")
            print(f"[{get_timestamp()}] 2. Enable JavaScript and cookies")
            print(f"[{get_timestamp()}] 3. Use realistic browser headers and timing")
            print(f"[{get_timestamp()}] 4. Avoid making too many concurrent requests")
            
        elif protection_type == "DataDome":
            print(f"[{get_timestamp()}] DataDome protection detected.")
            print(f"[{get_timestamp()}] RECOMMENDATIONS:")
            print(f"[{get_timestamp()}] 1. DataDome analyzes behavioral patterns")
            print(f"[{get_timestamp()}] 2. Implement very human-like browsing patterns")
            print(f"[{get_timestamp()}] 3. Use mouse movements and realistic timing")
            print(f"[{get_timestamp()}] 4. Rotate IP addresses frequently")
            
        else:
            print(f"[{get_timestamp()}] General anti-bot protection detected.")
            print(f"[{get_timestamp()}] RECOMMENDATIONS:")
            print(f"[{get_timestamp()}] 1. The site has enhanced anti-bot protection")
            print(f"[{get_timestamp()}] 2. Try using a different network/IP address")
            print(f"[{get_timestamp()}] 3. Consider using residential proxies")
            print(f"[{get_timestamp()}] 4. The site may need manual browser access first")
            print(f"[{get_timestamp()}] 5. Try running the scraper from a different environment")
            
        print(f"[{get_timestamp()}] === END PROTECTION GUIDANCE ===")

    def _check_page_health(self) -> Tuple[bool, str]:
        """Check if the page loaded properly and isn't blocked."""
        try:
            page_source = self.webdriver_manager.driver.page_source
            page_title = self.webdriver_manager.driver.title
            page_source_length = len(page_source)
            
            # Check for anti-bot protection first
            is_blocked, protection_type = self.webdriver_manager.is_blocked_by_protection(page_source, page_title)
            if is_blocked:
                return False, f"Blocked by {protection_type} protection"
            
            # Check for very small page content (likely incomplete load)
            if page_source_length < 500:
                return False, f"Page content too small ({page_source_length} chars) - possible loading issue"
            
            # Check for empty or suspicious title
            if not page_title or len(page_title.strip()) == 0:
                return False, "Empty page title - possible loading issue"
            
            # Check if page has minimal HTML structure
            essential_tags = ['body', 'div']
            missing_tags = []
            for tag in essential_tags:
                if f'<{tag}' not in page_source.lower():
                    missing_tags.append(tag)
            
            if missing_tags:
                return False, f"Missing essential HTML tags: {missing_tags}"
            
            return True, "Page appears healthy"
            
        except Exception as e:
            return False, f"Error checking page health: {str(e)}"

    def scrape_products(self) -> List[Dict[str, Any]]:
        """Main scraping flow for ETB sites."""
        if not self.base_url:
            print(f"[{get_timestamp()}] ERROR: No URL provided for scraping")
            print(f"[{get_timestamp()}] TROUBLESHOOTING: Set SCRAPING_URL_INTL_ETB environment variable")
            return []
        
        try:
            print(f"[{get_timestamp()}] === ETB SCRAPER STARTING ===")
            print(f"[{get_timestamp()}] Target URL: {self.base_url}")
            
            # Setup driver
            print(f"[{get_timestamp()}] Setting up browser driver...")
            if not self.webdriver_manager.setup_driver():
                print(f"[{get_timestamp()}] ERROR: Failed to setup browser driver")
                print(f"[{get_timestamp()}] TROUBLESHOOTING: Check if Chrome/Chromium is installed")
                print(f"[{get_timestamp()}] TROUBLESHOOTING: Install with: sudo apt-get install chromium-browser")
                return []
            
            self.product_extractor = ETBProductExtractor(self.webdriver_manager.driver)
            print(f"[{get_timestamp()}] Browser driver ready")
            
            # Navigate to the page
            print(f"[{get_timestamp()}] Navigating to ETB page...")
            try:
                self.webdriver_manager.driver.get(self.base_url)
                print(f"[{get_timestamp()}] Navigation successful")
            except Exception as e:
                error_msg = str(e)
                print(f"[{get_timestamp()}] ERROR: Navigation failed: {error_msg}")
                
                # Provide more specific troubleshooting based on error type
                if "ERR_NAME_NOT_RESOLVED" in error_msg:
                    print(f"[{get_timestamp()}] TROUBLESHOOTING: DNS resolution failed")
                    print(f"[{get_timestamp()}] - Check if {self.base_url} is accessible")
                    print(f"[{get_timestamp()}] - Verify internet connection")
                    print(f"[{get_timestamp()}] - The site may be blocked in this environment")
                elif "ERR_INTERNET_DISCONNECTED" in error_msg:
                    print(f"[{get_timestamp()}] TROUBLESHOOTING: No internet connection")
                elif "ERR_CONNECTION_TIMED_OUT" in error_msg:
                    print(f"[{get_timestamp()}] TROUBLESHOOTING: Connection timeout")
                    print(f"[{get_timestamp()}] - Site may be temporarily unavailable")
                    print(f"[{get_timestamp()}] - Try again later or use a different network")
                else:
                    print(f"[{get_timestamp()}] TROUBLESHOOTING: Check internet connection and URL accessibility")
                return []
            
            # Wait for page to load completely with human-like timing
            print(f"[{get_timestamp()}] Waiting for page to load completely...")
            initial_wait = random.uniform(8, 12)
            print(f"[{get_timestamp()}] Initial wait: {initial_wait:.1f} seconds...")
            time.sleep(initial_wait)
            
            # Comprehensive page loading validation
            current_url = self.webdriver_manager.driver.current_url
            page_title = self.webdriver_manager.driver.title
            page_source = self.webdriver_manager.driver.page_source
            page_source_length = len(page_source)
            
            print(f"[{get_timestamp()}] Page loaded - URL: {current_url}")
            print(f"[{get_timestamp()}] Page title: '{page_title}'")
            print(f"[{get_timestamp()}] Page source size: {page_source_length} characters")
            
            # Check overall page health
            page_healthy, health_message = self._check_page_health()
            print(f"[{get_timestamp()}] Page health check: {health_message}")
            
            if not page_healthy:
                if "Blocked by" in health_message:
                    protection_type = health_message.split("Blocked by ")[1].split(" protection")[0]
                    print(f"[{get_timestamp()}] === ANTI-BOT PROTECTION DETECTED ===")
                    print(f"[{get_timestamp()}] Protection type: {protection_type}")
                    print(f"[{get_timestamp()}] Page source sample: {page_source[:200]}...")
                    print(f"[{get_timestamp()}] ==========================================")
                    
                    # Try retry strategies
                    retry_success = self._handle_protection_retry(protection_type)
                    if not retry_success:
                        print(f"[{get_timestamp()}] ERROR: Unable to bypass {protection_type} protection")
                        self._print_protection_specific_guidance(protection_type)
                        return []
                    
                    # If retry successful, recheck page health
                    page_healthy, health_message = self._check_page_health()
                    print(f"[{get_timestamp()}] Post-retry page health: {health_message}")
                else:
                    # Non-protection related issue
                    print(f"[{get_timestamp()}] WARNING: Page loading issue detected")
                    print(f"[{get_timestamp()}] Issue: {health_message}")
                    print(f"[{get_timestamp()}] Attempting to continue with limited functionality...")
            
            # Update page info after any retries
            current_url = self.webdriver_manager.driver.current_url
            page_title = self.webdriver_manager.driver.title
            page_source = self.webdriver_manager.driver.page_source
            page_source_length = len(page_source)
            
            # Wait for products to load with enhanced detection
            print(f"[{get_timestamp()}] Initiating product detection...")
            product_elements = self.product_extractor.wait_for_products_to_load(timeout=30)
            
            if not product_elements:
                # Check one more time if we're being blocked
                final_page_source = self.webdriver_manager.driver.page_source
                final_page_title = self.webdriver_manager.driver.title
                is_still_blocked, final_protection_type = self.webdriver_manager.is_blocked_by_protection(
                    final_page_source, final_page_title
                )
                
                print(f"[{get_timestamp()}] === NO PRODUCTS FOUND ===")
                if is_still_blocked:
                    print(f"[{get_timestamp()}] CAUSE: Page is still blocked by {final_protection_type} protection")
                    print(f"[{get_timestamp()}] Page content sample: {final_page_source[:150]}...")
                else:
                    print(f"[{get_timestamp()}] Page appears to have loaded but no products detected")
                    
                print(f"[{get_timestamp()}] TROUBLESHOOTING SUMMARY:")
                print(f"[{get_timestamp()}] 1. Check if the website is accessible manually")
                if is_still_blocked:
                    print(f"[{get_timestamp()}] 2. Site is using {final_protection_type} anti-bot protection")
                    print(f"[{get_timestamp()}] 3. Try accessing from a different IP/network")
                    print(f"[{get_timestamp()}] 4. Consider using residential proxies")
                else:
                    print(f"[{get_timestamp()}] 2. The site might use heavy JavaScript/SPA - check browser console")
                    print(f"[{get_timestamp()}] 3. CSS selectors might be outdated for this site")
                print(f"[{get_timestamp()}] 5. Check debug screenshots in /tmp/debug_screenshots/")
                print(f"[{get_timestamp()}] ============================")
                return []
            
            # Extract product information
            products = []
            print(f"[{get_timestamp()}] === PRODUCT EXTRACTION ===")
            print(f"[{get_timestamp()}] Extracting information from {len(product_elements)} ETB products...")
            
            extraction_errors = 0
            for idx, element in enumerate(product_elements):
                try:
                    product = self.product_extractor.extract_product_info(element)
                    if product:
                        products.append(product)
                        if len(products) % 5 == 0:  # More frequent progress
                            print(f"[{get_timestamp()}] Processed {len(products)}/{len(product_elements)} products...")
                    else:
                        extraction_errors += 1
                except Exception as e:
                    print(f"[{get_timestamp()}] Error processing product {idx+1}: {str(e)}")
                    extraction_errors += 1
                    continue
            
            success_rate = (len(products) / len(product_elements)) * 100 if product_elements else 0
            print(f"[{get_timestamp()}] === EXTRACTION COMPLETE ===")
            print(f"[{get_timestamp()}] Products found: {len(products)}")
            print(f"[{get_timestamp()}] Extraction errors: {extraction_errors}")
            print(f"[{get_timestamp()}] Success rate: {success_rate:.1f}%")
            
            # Show sample product data if found
            if products:
                sample_product = products[0]
                print(f"[{get_timestamp()}] Sample product:")
                print(f"[{get_timestamp()}]   Name: {sample_product.get('name', 'N/A')}")
                print(f"[{get_timestamp()}]   Price: {sample_product.get('priceShow', 'N/A')}")
                print(f"[{get_timestamp()}]   URL: {sample_product.get('url', 'N/A')[:100]}...")
            
            print(f"[{get_timestamp()}] ETB scraping completed successfully")
            return products
            
        except Exception as e:
            print(f"[{get_timestamp()}] FATAL ERROR in ETB scraper: {str(e)}")
            import traceback
            print(f"[{get_timestamp()}] Full traceback: {traceback.format_exc()}")
            return []
        finally:
            try:
                self.webdriver_manager.quit_driver()
                print(f"[{get_timestamp()}] Browser driver closed")
            except:
                pass


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
