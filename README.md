# Alert - Product Availability Scraper

A Python-based web scraping system that monitors product availability on e-commerce platforms (Lazada and Pokemon Center) and sends notifications via Telegram when target products become available.

## Overview

This project consists of multiple scrapers that:
1. Fetch product data from e-commerce JSON APIs
2. Filter products based on configurable criteria
3. Send Telegram notifications for available products
4. Run automatically on a schedule via GitHub Actions

## Product Name Filter (TCG/Trading Cards)

**The scrapers filter products to only show items related to Trading Card Games (TCG).**

### Filter Location

The TCG filter is implemented in two files:

1. **`scraper_common.py`** - Lines 145-163 (function: `filter_available_products()`)
2. **`scraper_intl.py`** - Lines 283-301 (function: `filter_available_products()`)

### Filter Behavior

By default, the filter only considers products that:
- Are marked as "in stock" (`inStock == True`)
- Contain **"TCG"** or **"Trading"** in the product name (case-insensitive)

This means only Trading Card Game related products will trigger notifications.

### Making the Filter Configurable

You can customize the filter keywords using the `PRODUCT_NAME_FILTERS` environment variable:

```bash
# Default behavior (TCG or Trading)
PRODUCT_NAME_FILTERS="TCG,Trading"

# Custom filters (comma-separated, case-insensitive)
PRODUCT_NAME_FILTERS="Pokemon,Card,Booster"

# Single filter
PRODUCT_NAME_FILTERS="Elite Trainer Box"

# Disable filtering (match all in-stock products)
PRODUCT_NAME_FILTERS=""
```

#### Setting in GitHub Actions

Add to your workflow file or repository secrets:

```yaml
env:
  PRODUCT_NAME_FILTERS: "TCG,Trading,Pokemon"
```

Or in GitHub repository settings: Settings → Secrets and Variables → Actions → Variables → New repository variable

## Files

### Main Scrapers

- **`scraper.py`** - Primary Lazada scraper (uses `SCRAPING_URL`)
- **`scraper2.py`** - Secondary Lazada scraper with custom headers (uses `SCRAPING_URL_2`)
- **`scraper_intl.py`** - International/Pokemon Center scraper with anti-bot measures (uses `SCRAPING_URL_INTL`)

### Shared Components

- **`scraper_common.py`** - Common functions used by scrapers:
  - `fetch_json()` - Fetch and parse JSON from URLs
  - `extract_products_from_payload()` - Parse product data
  - `filter_available_products()` - **Apply TCG filter** ⭐
  - `log_all_products_sorted()` - Display all products

- **`notification_service.py`** - Telegram notification service

### Configuration

Environment variables used:
- `SCRAPING_URL` - Target URL for scraper.py
- `SCRAPING_URL_2` - Target URL for scraper2.py  
- `SCRAPING_URL_INTL` - Target URL for scraper_intl.py
- `TELEGRAM_BOT_TOKEN` - Telegram bot authentication token
- `TELEGRAM_CHANNEL_ID` - Telegram channel/chat ID for notifications
- `PRODUCT_NAME_FILTERS` - Comma-separated filter keywords (default: "TCG,Trading")

## Installation

```bash
# Clone repository
git clone https://github.com/kingyx3/alert.git
cd alert

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running Locally

```bash
# Set environment variables
export SCRAPING_URL="https://your-target-url.com/api/products"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHANNEL_ID="your-channel-id"
export PRODUCT_NAME_FILTERS="TCG,Trading"  # Optional

# Run scrapers
python scraper.py
python scraper2.py
python scraper_intl.py
```

### GitHub Actions

The scrapers run automatically via GitHub Actions workflows in `.github/workflows/`:
- `scraper0.yml` to `scraper50.yml` - Scheduled runs at different intervals
- `scraper.yml` - Manual trigger workflow
- `scraper_intl.yml` - International scraper workflow

## How It Works

1. **Fetch** - Scrapers fetch JSON data from configured URLs
2. **Parse** - Extract product information (name, price, stock status, URL)
3. **Filter** - Apply availability and name filters (TCG/Trading by default)
4. **Log** - Display all products (sorted alphabetically)
5. **Notify** - Send Telegram messages for filtered products
6. **Save** - Store results in timestamped JSON files

## Modifying the Filter

To change what products are monitored:

### Option 1: Environment Variable (Recommended)

Set `PRODUCT_NAME_FILTERS` to your desired keywords:
```bash
export PRODUCT_NAME_FILTERS="Pokemon,Charizard,Pikachu"
```

### Option 2: Code Modification

Edit the `filter_available_products()` function in:
- `scraper_common.py` (lines 145-163)
- `scraper_intl.py` (lines 283-301)

Example - Add additional filters:
```python
def filter_available_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def contains_keywords(product_name: str) -> bool:
        if not product_name:
            return False
        name_lower = product_name.lower()
        # Add your keywords here
        return any(keyword in name_lower for keyword in ["tcg", "trading", "pokemon", "booster"])
    
    available = [
        p for p in products 
        if p.get("inStock") is True and contains_keywords(p.get("name", ""))
    ]
    return available
```

## Output

### Console Output
- Timestamp-prefixed log messages
- Sorted list of all scraped products
- Availability status for each product
- Summary statistics

### File Output
- `available_products_[timestamp].json` - Filtered available products
- `raw_payload_[timestamp].json` - Debug output when no products found

## Dependencies

- `requests>=2.31.0` - HTTP requests library
- `pytelegrambotapi>=4.14.0` - Telegram Bot API wrapper

## License

See repository license file.

## Troubleshooting

### No products found
- Check the `raw_payload_*.json` debug file
- Verify the scraping URL is correct
- The site may have changed its API structure

### No notifications sent
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` are set correctly
- Check that filtered products exist (TCG/Trading filter may exclude all products)
- Try setting `PRODUCT_NAME_FILTERS=""` to disable filtering temporarily

### Bot detection (scraper_intl.py)
- The international scraper includes anti-bot measures
- Uses rotating user agents and referrer simulation
- If still blocked, increase delays or reduce scraping frequency
