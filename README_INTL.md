# International ETB Scraper Requirements

This document explains the requirements and setup for the International ETB Scraper (`scraper_intl.py`).

## Overview

The International ETB Scraper is a specialized web scraping module designed for international ETB e-commerce sites using Selenium WebDriver. It provides custom scraping components specifically optimized for ETB sites.

## Dependencies

The scraper requires the following Python packages, which are specified in `requirements_intl.txt`:

### Core Dependencies

1. **selenium>=4.36.0** - Web browser automation framework
   - Used for dynamic content scraping
   - Handles JavaScript-heavy e-commerce sites
   - Required for all WebDriver functionality

2. **webdriver-manager>=4.0.2** - Automatic WebDriver management  
   - Automatically downloads and manages Chrome WebDriver
   - Fallback when system chromedriver is not available
   - Simplifies deployment across different environments

### Optional Dependencies

3. **requests>=2.31.0** - HTTP library
   - May be used for API calls or direct HTTP requests
   - Required by other components in the system

4. **pytelegrambotapi>=4.14.0** - Telegram Bot API
   - Required for notification functionality
   - Integrates with the notification service

## Installation

### Method 1: Install International Scraper Requirements

```bash
pip install -r requirements_intl.txt
```

### Method 2: Install Individual Packages

```bash
pip install selenium>=4.36.0 webdriver-manager>=4.0.2
```

## System Requirements

- **Python 3.6+**
- **Chrome Browser** - Required for Selenium WebDriver
- **Linux/Unix environment** - The scraper looks for chromedriver at `/usr/bin/chromedriver`

### Chrome Browser Installation (Ubuntu/Debian)

```bash
# Update package lists
sudo apt update

# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install google-chrome-stable
```

## Usage

### Basic Usage

```bash
# Set the required environment variable
export SCRAPING_URL_INTL_ETB="https://your-etb-site.com"

# Run the scraper
python3 scraper_intl.py
```

### Environment Variables

- **SCRAPING_URL_INTL_ETB** (Required) - The ETB site URL to scrape
- **TELEGRAM_BOT_TOKEN** (Optional) - For notification functionality

## Graceful Degradation

The scraper is designed with graceful degradation:

- **If Selenium is not installed**: The scraper will report that selenium is unavailable and exit gracefully
- **If Chrome/chromedriver is not available**: The scraper will attempt to use webdriver-manager as a fallback
- **If webdriver-manager fails**: The scraper will report the failure and exit gracefully

## Error Handling

The scraper includes comprehensive error handling:

1. **Missing dependencies** - Clearly reports missing packages
2. **Browser setup failures** - Reports WebDriver setup issues  
3. **Network errors** - Handles connection failures gracefully
4. **Invalid URLs** - Validates environment variables

## Differences from Main Scraper

Unlike the main `scraper.py` which uses HTTP requests for JSON APIs, `scraper_intl.py`:

- Uses Selenium WebDriver for browser automation
- Handles JavaScript-rendered content
- Includes anti-detection measures for ETB sites
- Has custom product extraction logic for ETB site structures

## Testing

To test if the requirements are properly installed:

```bash
# Test with missing URL (should show error message)
python3 scraper_intl.py

# Test with example URL (should attempt to scrape)
SCRAPING_URL_INTL_ETB="https://example.com" python3 scraper_intl.py
```

Expected output with proper installation:
- Should load without import errors
- Should report selenium availability
- Should attempt WebDriver setup (even if it fails due to invalid URL)

## Troubleshooting

### "Selenium is not installed/available"
```bash
pip install selenium>=4.36.0
```

### "Failed to setup Chrome driver with webdriver manager"
```bash
pip install webdriver-manager>=4.0.2
# Or install Chrome browser manually
```

### Import errors
```bash
pip install -r requirements_intl.txt
```

## Files

- `scraper_intl.py` - Main international scraper module
- `requirements_intl.txt` - Python package requirements
- `README_INTL.md` - This documentation file