# Alert - Configurable Web Scraper

A configurable web scraper that handles dynamically loaded content from various e-commerce stores.

## Features

- **Dynamic Content Support**: Uses Selenium WebDriver to handle JavaScript-loaded products
- **Automatic Fallback**: Falls back to basic HTTP scraping if browser automation fails
- **Robust Error Handling**: Gracefully handles various error conditions
- **Multiple Product Selectors**: Tries various CSS selectors to find products
- **Product Availability & Price Detection**: Extracts price information and uses buy button indicators ('Buy Now', 'Add to Cart', etc.) for availability detection
- **Smart URL Processing**: Handles both absolute and relative product URLs

## Requirements

- Python 3.7+
- Chrome browser
- ChromeDriver (automatically managed)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Configuration

Set the target URL using the `SCRAPING_URL` environment variable:

```bash
export SCRAPING_URL="https://your-target-store.com/products"
python scraper.py
```

If no `SCRAPING_URL` is provided, it will use the default URL as fallback.

### Running the Scraper

```bash
python scraper.py
```

The scraper will:
1. Launch a headless Chrome browser
2. Navigate to the configured store page
3. Wait for products to load dynamically (up to 30 seconds)
4. Extract product information (title, price, image, URL)
5. Check each product URL for availability and price (detection based on buy options like 'Buy Now', 'Add to Cart')
6. Display only available products and save results to JSON file

## How It Works

The scraper addresses the common issue where e-commerce sites load products via JavaScript after the initial page load. Traditional HTTP-based scrapers only see the initial HTML skeleton, missing the actual product data.

This scraper:
- Uses Selenium WebDriver to execute JavaScript
- Implements intelligent waiting for dynamic content
- Tries multiple CSS selectors to locate products
- Handles various page layouts and structures
- Filters products by checking individual product pages for availability
- Returns only products that contain "Buy Now" button text
- **NEW**: Stores scraping results in formatted text and sends notifications to Telegram

## Notification Features

The scraper now includes integrated Telegram channel notification capabilities:

### Features
- **Telegram Channel**: Sends formatted product notifications to a configured Telegram channel
- **Text Formatting**: Converts scraping results into user-friendly messages with emojis
- **Error Handling**: Gracefully handles missing credentials and failed notifications
- **Long Message Support**: Automatically splits messages exceeding Telegram's character limit

### Setup for Notifications

1. **Telegram Bot Setup**:
   ```bash
   # Set bot token from @BotFather
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
   ```

2. **Telegram Channel Setup**:
   ```bash
   # Set channel ID (negative number for channels)
   export TELEGRAM_CHANNEL_ID="-1001234567890"
   ```

3. **For GitHub Actions (recommended)**:
   - Store `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` as repository secrets
   - The scraper will automatically use these when running in GitHub Actions

### Demo Scripts
- `demo_notification.py` - Test notification service with mock data
- `config_example.py` - Configuration examples and setup instructions