# ETB Scraper Enhanced Debugging Guide

## Overview

The ETB scraper has been enhanced with comprehensive debugging capabilities to help diagnose why products are not being found. When the scraper fails to find products, it now provides detailed analysis and troubleshooting information.

## Enhanced Debugging Features

### 1. Comprehensive Page Analysis
- **Page Information**: URL, title, source size validation
- **Screenshot Capture**: Automatic screenshots saved to `/tmp/debug_screenshots/`
- **Page Source Capture**: HTML source saved for manual inspection
- **Error Detection**: Checks for 404 errors, Cloudflare protection, CAPTCHA, etc.

### 2. Element Count Analysis
Analyzes the quantity of common HTML elements:
- `div`, `section`, `article`, `main`, `ul`, `li`, `span`, `p`, headers, images, buttons
- Helps identify if the page loaded properly

### 3. E-commerce Pattern Analysis
Searches for elements with e-commerce related CSS classes:
- `product`, `item`, `card`, `grid`, `list`, `shop`, `buy`, `price`, `cart`, `add`
- Shows how many elements contain each pattern

### 4. Link Analysis
- **Total Links**: Count of all links on the page
- **Product Links**: Links that match product URL patterns
- **Sample Links**: Shows examples of actual URLs found
- **Link Categorization**: Internal vs external links

### 5. CSS Class & ID Analysis
- **Class Discovery**: Finds all unique CSS class names
- **Pattern Matching**: Identifies product-related and price-related classes
- **Complex Classes**: Shows compound class names that might indicate modern frameworks

### 6. Selector Testing
Tests all current selectors and shows results:
- **ETB Product Selectors**: Tests primary product detection selectors
- **Price Selectors**: Tests price-based fallback selectors
- **Title Selectors**: Tests title extraction selectors

### 7. HTML Structure Sampling
- **Meta Tags**: Counts meta tags (indicates page completeness)
- **Script Tags**: Identifies JavaScript-heavy pages
- **SPA Detection**: Checks for Single Page Application indicators
- **Framework Detection**: Looks for common e-commerce frameworks

### 8. Content Analysis
- **Keyword Detection**: Searches for product-related terms
- **Text Length**: Validates page has meaningful content
- **Content Quality**: Warns about pages that may not have loaded

## Fallback Detection Strategies

The enhanced scraper uses 6 different strategies when primary selectors fail:

### Strategy 1: Price-based Detection
- Tests 10 different price selectors
- Shows sample price text found
- Gets parent containers of price elements
- **Output**: Reports which selectors found prices and how many containers resulted

### Strategy 2: Pattern-based Detection
- Analyzes all links for product URL patterns
- Tests 8 different CSS selector patterns
- Filters elements that look like products
- **Output**: Shows link analysis and pattern matching results

### Strategy 3: Generic Container Detection
- Looks for repetitive HTML structures
- Tests 7 different generic selectors
- Scores elements based on product likelihood
- **Output**: Reports element counts and content quality

### Strategy 4: Advanced DOM Analysis
- Finds elements with similar sibling structures
- Groups by parent to identify product listings
- Uses advanced product detection scoring
- **Output**: Shows container patterns and scoring results

### Strategy 5: Comprehensive Page Analysis
- Full debugging output (described above)
- Takes screenshots for manual inspection
- Provides detailed troubleshooting guidance

### Strategy 6: Dynamic Content Detection
- Waits for dynamically loaded content
- Tests data attributes used by modern frameworks
- Attempts scroll-based detection for infinite scroll
- **Output**: Reports dynamic selectors and scroll behavior

## Troubleshooting Output

When no products are found, the scraper provides:

```
=== NO PRODUCTS FOUND ===
TROUBLESHOOTING SUMMARY:
1. Check if the website is accessible manually
2. The site might use heavy JavaScript/SPA - check browser console  
3. Site might have anti-bot protection
4. CSS selectors might be outdated
5. Check debug screenshots in /tmp/debug_screenshots/
============================
```

## Debug Files Generated

### Screenshots
- **Location**: `/tmp/debug_screenshots/debug_page_YYYYMMDD_HHMMSS.png`
- **Purpose**: Visual inspection of how the page appears to the browser
- **Usage**: Check if page loaded correctly, see actual layout

### Page Source
- **Location**: `/tmp/debug_screenshots/debug_page_source_YYYYMMDD_HHMMSS.html`
- **Purpose**: Raw HTML for manual analysis
- **Usage**: Search for product elements, check for JavaScript frameworks

## Usage Examples

### Running with Enhanced Debugging
```bash
export SCRAPING_URL_INTL_ETB="https://www.example-shop.com/products"
python3 scraper_intl.py
```

### Analyzing Debug Output
1. **Check Console Output**: Look for specific error messages and selector test results
2. **Review Screenshots**: Open PNG files to see visual page state  
3. **Inspect HTML Source**: Search HTML files for product-related elements
4. **Update Selectors**: Based on findings, update ETB_PRODUCT_SELECTORS

### Common Issues and Solutions

| Issue | Indicators | Solution |
|-------|------------|----------|
| **Page didn't load** | Very small page source, empty title | Check URL accessibility, network issues |
| **JavaScript/SPA site** | Many script tags, SPA detection = True | May need dynamic content detection, longer waits |
| **Anti-bot protection** | Cloudflare, CAPTCHA detected | May need different user agents, headers |
| **Wrong selectors** | Elements found but no products extracted | Update CSS selectors based on HTML analysis |

## Element Scoring System

The enhanced scraper includes an intelligent element scoring system:

- **Images**: +2 points (products usually have images)
- **Product URLs**: +2 points (links that look like product pages)
- **Price indicators**: +3 points (text containing $, €, "price", etc.)
- **Action words**: +1 point ("buy", "add", "cart", etc.)  
- **Product classes**: +3 points (CSS classes containing "product", "item", etc.)
- **Reasonable size**: +1 point (elements with reasonable dimensions)

Elements with score ≥ 3 are considered likely products.

## Future Enhancements

The debugging system can be extended with:
- **Performance metrics** (page load time, element detection time)
- **A/B testing** of different selector strategies
- **Machine learning** based element classification
- **Visual diff detection** to track page changes over time