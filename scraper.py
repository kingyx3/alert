#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time

class Scraper:
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

            print(f"[{datetime.now()}] Scraping completed. Found {len(products)} products.")

            # Display results
            self.display_results(products)

            return products

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

        if title or price:  # Only return if we have some useful information
            product = {
                'title': title or 'No title available',
                'price': price or 'Price not available',
                'image': image_url,
                'url': product_url,
                'scraped_at': datetime.now().isoformat()
            }
            return product

        return None

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

    def display_results(self, products):
        """Display the scraped products in a formatted way"""
        print(f"\n{'='*80}")
        print(f"POKEMON STORE SCRAPING RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        if not products:
            print("No products found.")
            return

        for idx, product in enumerate(products, 1):
            print(f"\n{idx}. {product['title']}")
            print(f"   Price: {product['price']}")
            if product['url']:
                print(f"   URL: {product['url']}")
            if product['image']:
                print(f"   Image: {product['image']}")
            print(f"   Scraped: {product['scraped_at']}")

        print(f"\n{'='*80}")
        print(f"Total products found: {len(products)}")
        print(f"{'='*80}\n")

def main():
    """Main function to run the scraper"""
    print(f"[{datetime.now()}] Scraper starting...")

    scraper = Scraper()
    products = scraper.scrape_products()

    # Optional: Save results to JSON file
    if products:
        print('products', products)
        filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            print(f"[{datetime.now()}] Results saved to {filename}")
        except Exception as e:
            print(f"[{datetime.now()}] Error saving results: {str(e)}")

    print(f"[{datetime.now()}] Scraper completed.")

if __name__ == "__main__":
    main()