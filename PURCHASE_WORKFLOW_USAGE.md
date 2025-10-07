# Purchase Workflow Usage Guide

This guide explains how to use the new `purchase_workflow.py` module to automatically purchase products when `scraper.py` detects availability.

## Overview

The purchase workflow is a **separate module** that can be triggered when `scraper.py` finds available products. It uses selenium-based browser automation to navigate to product pages and click "Buy Now" buttons.

## Basic Usage

### 1. Import the workflow function

```python
from purchase_workflow import trigger_purchase_workflow
```

### 2. Call it when products are available

```python
# After scraper.py detects available products:
available_products = filter_available_products(products)

if available_products:
    # Trigger the purchase workflow
    results = trigger_purchase_workflow(available_products)
    
    # Check results
    if results['success']:
        print(f"Purchase workflow completed")
        print(f"Successful purchases: {results['summary']['successful_purchases']}")
    else:
        print(f"Purchase workflow failed: {results.get('error')}")
```

## Integration with scraper.py

### Option 1: Modify scraper.py directly

Add these lines to `scraper.py` after the availability detection:

```python
# After this line in scraper.py:
available_products = filter_available_products(products)

# Add this:
if available_products:
    try:
        from purchase_workflow import trigger_purchase_workflow
        print(f"[{get_timestamp()}] Triggering purchase workflow...")
        purchase_results = trigger_purchase_workflow(available_products)
        if purchase_results.get('success'):
            print(f"[{get_timestamp()}] Purchase workflow completed successfully")
        else:
            print(f"[{get_timestamp()}] Purchase workflow failed")
    except ImportError:
        print(f"[{get_timestamp()}] Purchase workflow not available")
    except Exception as e:
        print(f"[{get_timestamp()}] Error in purchase workflow: {str(e)}")
```

### Option 2: Use the provided integration example

Run the enhanced scraper that includes purchase workflow:

```bash
python3 scraper_with_purchase_integration.py
```

This combines the original scraper.py functionality with automatic purchase workflow triggering.

## Expected Product Format

The workflow expects products in the format returned by `scraper.py`:

```python
{
    "name": "Product Name",           # or "title"
    "price": 99.99,
    "inStock": True,
    "url": "https://example.com/product",
    "priceShow": "$99.99",
    # ... other fields
}
```

## Workflow Process

When triggered, the workflow:

1. **Sets up browser** using selenium WebDriver
2. **For each available product**:
   - Navigates to the product URL
   - Takes a screenshot (before purchase)
   - Finds "Buy Now" button using smart detection
   - Clicks the button
   - Takes a screenshot (after purchase)
   - Logs the result
3. **Cleans up** browser resources
4. **Returns results** with detailed purchase attempt information

## Results Format

The workflow returns a dictionary with:

```python
{
    "success": True,
    "timestamp": "2025-10-07T16:08:12.253633",
    "purchase_attempts": [
        {
            "product": "Product Name",
            "url": "https://example.com/product",
            "purchase_success": True,
            "purchase_message": "Buy now button clicked successfully",
            "timestamp": "2025-10-07 16:08:12"
        }
    ],
    "summary": {
        "total_products": 2,
        "purchase_attempts": 2,
        "successful_purchases": 1,
        "failed_purchases": 1
    }
}
```

## Button Detection

The workflow uses multiple strategies to find "Buy Now" buttons:

1. **CSS Selectors**:
   - `[data-qa-locator*="buy-now"]`
   - `[data-testid*="add-to-cart"]`
   - `.buy-now-button`, `.add-to-cart`
   - `button[class*="buy-now"]`

2. **Text-based Detection**:
   - Buttons containing "buy now"
   - Buttons containing "add to cart"  
   - Buttons containing "purchase"

## Screenshots

The workflow automatically captures screenshots:
- `before_purchase_YYYYMMDD_HHMMSS.png` - Before clicking buy button
- `after_purchase_click_YYYYMMDD_HHMMSS.png` - After clicking buy button

## Error Handling

The workflow gracefully handles:
- Selenium not available
- Invalid product URLs
- Pages that fail to load
- Missing buy buttons
- Browser setup failures

## Requirements

- Python 3.6+
- Selenium WebDriver (optional - workflow will report unavailability)
- Chrome browser and chromedriver (for selenium functionality)

## Testing

Run the test suite to verify functionality:

```bash
python3 test_purchase_workflow.py
```

## Files Created

- `purchase_workflow.py` - Main workflow module
- `scraper_with_purchase_integration.py` - Integration example
- `PURCHASE_WORKFLOW_USAGE.md` - This documentation
- `purchase_results_YYYYMMDD_HHMMSS.json` - Results saved by workflow