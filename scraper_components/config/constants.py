#!/usr/bin/env python3
"""
Configuration constants for web scraping operations.

This module contains all the selectors, timeouts, and other constants
used throughout the scraping process.
"""

# ---------- Browser Configuration ----------
DEFAULT_WINDOW_SIZE = "1920,1080"
SYSTEM_CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

# ---------- CSS Selectors ----------
# Common selectors for product listing pages
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

# ---------- Content Indicators ----------
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