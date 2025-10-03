#!/usr/bin/env python3

"""
Demo script to show the enhanced scraper functionality
This creates a mock scenario to demonstrate the feature
"""

from unittest.mock import patch, MagicMock
from scraper import Scraper
from datetime import datetime

def create_mock_response(content):
    """Helper to create mock HTTP responses"""
    mock_response = MagicMock()
    mock_response.content = content.encode('utf-8')
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    return mock_response

def demo_enhanced_scraper():
    """Demo the enhanced scraper with mock product data"""
    print(f"[{datetime.now()}] Demo: Enhanced Product Scraper")
    print("="*80)
    
    scraper = Scraper()
    
    # Mock the main page response with product links
    main_page_html = """
    <html>
    <body>
        <div class="product-item">
            <h3>Pokemon Premium Card Pack</h3>
            <span class="price">$29.99</span>
            <a href="/product/premium-pack">View Product</a>
        </div>
        <div class="product-item">
            <h3>Pokemon Standard Edition Deck</h3>
            <span class="price">$19.99</span>
            <a href="/product/standard-deck">View Product</a>
        </div>
        <div class="product-item">
            <h3>Pokemon Special Collection</h3>
            <span class="price">$39.99</span>
            <a href="/product/special-collection">View Product</a>
        </div>
    </body>
    </html>
    """
    
    # Mock individual product page responses
    product_responses = {
        'https://www.lazada.sg/product/premium-pack': """
            <html><body>
                <h1>Pokemon Premium Card Pack</h1>
                <p>This is a premium collection with exclusive cards!</p>
                <div class="stock-status">In Stock - Ready to Ship</div>
            </body></html>
        """,
        'https://www.lazada.sg/product/standard-deck': """
            <html><body>
                <h1>Pokemon Standard Edition Deck</h1>
                <p>Basic starter deck for beginners</p>
                <div class="stock-status">Available Now</div>
            </body></html>
        """,
        'https://www.lazada.sg/product/special-collection': """
            <html><body>
                <h1>Pokemon Special Collection</h1>
                <p>Limited edition collector's set</p>
                <div class="stock-status">Currently Out of Stock</div>
            </body></html>
        """
    }
    
    def mock_get(url, **kwargs):
        if url == scraper.base_url:
            return create_mock_response(main_page_html)
        elif url in product_responses:
            return create_mock_response(product_responses[url])
        else:
            # Default response for unknown URLs
            return create_mock_response("<html><body>Product not found</body></html>")
    
    # Mock the requests.get method
    with patch('requests.get', side_effect=mock_get):
        available_products = scraper.scrape_products()
    
    print(f"\n[{datetime.now()}] Demo Results Summary:")
    print(f"Available products found: {len(available_products)}")
    
    print(f"\n[{datetime.now()}] Product URLs that do NOT contain 'Out of stock' or 'Standard Edition':")
    for i, product in enumerate(available_products, 1):
        print(f"{i}. {product['title']}")
        print(f"   URL: {product['url']}")
        print(f"   Status: {product['availability_status']}")
        print()

if __name__ == "__main__":
    demo_enhanced_scraper()