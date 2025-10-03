# Alert - Pokemon Store Scraper

A web scraper for the Pokemon Store on Lazada that handles dynamically loaded content.

## Features

- **Dynamic Content Support**: Uses Selenium WebDriver to handle JavaScript-loaded products
- **Automatic Fallback**: Falls back to basic HTTP scraping if browser automation fails
- **Robust Error Handling**: Gracefully handles various error conditions
- **Multiple Product Selectors**: Tries various CSS selectors to find products
- **Product Availability Filtering**: Checks each product URL for "Buy Now" button text to determine availability
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

```bash
python scraper.py
```

The scraper will:
1. Launch a headless Chrome browser
2. Navigate to the Pokemon Store page
3. Wait for products to load dynamically (up to 30 seconds)
4. Extract product information (title, price, image, URL)
5. Check each product URL for availability (filters products based on "Buy Now" button presence)
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

The scraper now includes integrated Firebase and Telegram notification capabilities:

### Features
- **Firebase Integration**: Fetches Telegram chat IDs from Firebase Realtime Database
- **Telegram Bot**: Sends formatted product notifications to multiple chats
- **Text Formatting**: Converts scraping results into user-friendly messages with emojis
- **Error Handling**: Gracefully handles missing credentials and failed notifications
- **Batch Messaging**: Supports sending to multiple chat IDs simultaneously

### Setup for Notifications

1. **Firebase Setup**:
   ```bash
   # Set environment variables
   export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/serviceAccount.json"
   export FIREBASE_DATABASE_URL="https://your-project-id-default-rtdb.firebaseio.com/"
   ```

2. **Telegram Bot Setup**:
   ```bash
   # Set bot token from @BotFather
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
   ```

3. **Firebase Database Structure**:
   ```json
   {
     "telegram_chat_ids": [
       "123456789",
       "987654321",
       "-555666777"
     ]
   }
   ```

### Demo Scripts
- `demo_notification.py` - Test notification service with mock data
- `config_example.py` - Configuration examples and setup instructions