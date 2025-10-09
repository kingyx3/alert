# Enhanced ETB Scraper Usage Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements_intl.txt
   ```

2. **Install Chrome/Chromium**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install chromium-browser
   # or download Google Chrome
   ```

3. **Set environment variable**:
   ```bash
   export SCRAPING_URL_INTL_ETB="https://www.pokemoncenter.com/category/elite-trainer-box"
   ```

4. **Run the scraper**:
   ```bash
   python3 scraper_intl.py
   ```

## Enhanced Features in Action

When you run the enhanced scraper, you'll see output like:

```
[2025-10-09T13:15:23.837614] International ETB Scraper starting...
[2025-10-09T13:15:23.837636] Using international ETB URL: https://www.pokemoncenter.com/category/elite-trainer-box
[2025-10-09T13:15:23.837642] === ETB SCRAPER STARTING ===
[2025-10-09T13:15:23.837644] Target URL: https://www.pokemoncenter.com/category/elite-trainer-box
[2025-10-09T13:15:23.837646] Setting up browser driver...
[2025-10-09T13:15:32.426426] Applied realistic request headers via CDP    # ← NEW: CDP headers
[2025-10-09T13:15:32.426444] Browser driver ready
[2025-10-09T13:15:32.426444] Navigating to ETB page...
[2025-10-09T13:15:33.114406] Navigation successful
[2025-10-09T13:15:33.114418] Waiting for page to load completely...
[2025-10-09T13:15:33.114418] Initial wait: 10.3 seconds...               # ← NEW: Randomized timing
```

## Anti-Bot Protection Handling

### If Incapsula Protection is Detected:

```
[2025-10-09T13:15:38.137053] === ANTI-BOT PROTECTION DETECTED ===
[2025-10-09T13:15:38.137056] Protection type: Incapsula
[2025-10-09T13:15:38.137058] Attempting to bypass Incapsula protection...
[2025-10-09T13:15:38.137058] Trying strategy: Progressive delay with navigation    # ← NEW: 5 strategies
[2025-10-09T13:15:38.137058] Progressive delay attempt 1/3: 15 seconds...
```

### Enhanced Retry Strategies:

1. **Progressive delay with navigation** - Waits 15s, 30s, 45s with cache clearing
2. **Clear cookies and stealth reload** - Complete browser state reset
3. **Human-like browsing simulation** - Homepage navigation + scrolling
4. **Long wait and reload** - Extended delays
5. **Random delay retry** - Randomized timing

### Protection-Specific Guidance:

If all strategies fail, you'll get specific advice:

```
[2025-10-09T13:15:38.137058] === INCAPSULA PROTECTION BYPASS GUIDANCE ===
[2025-10-09T13:15:38.137058] Incapsula is an advanced bot protection system.
[2025-10-09T13:15:38.137058] RECOMMENDATIONS:
[2025-10-09T13:15:38.137058] 1. Try accessing the site manually in a browser first
[2025-10-09T13:15:38.137058] 2. Use residential IP addresses (not datacenter/VPS IPs)
[2025-10-09T13:15:38.137058] 3. Implement longer delays between requests (30-60 seconds)
[2025-10-09T13:15:38.137058] 4. Consider rotating user agents and browser fingerprints
[2025-10-09T13:15:38.137058] 5. Some Incapsula sites require JavaScript challenges to be solved
[2025-10-09T13:15:38.137058] 6. Try running from different geographic locations
```

## Advanced Configuration

### Custom User Agent

The scraper automatically rotates between 5 realistic user agents. To see which one is selected:

```python
from scraper_intl import ETBWebDriverManager
manager = ETBWebDriverManager()
print(f"Selected user agent: {manager.current_user_agent}")
```

### Custom Delays

For sites with stricter protection, you can modify the delays in the retry strategies:

```python
# In _retry_progressive_delay method
delays = [30, 60, 90]  # Longer delays for stricter sites
```

### Debug Mode

To see detailed debugging information:

1. Check `/tmp/debug_screenshots/` for screenshots
2. Review the comprehensive page analysis output
3. Monitor the protection detection logs

## Troubleshooting Common Issues

### 1. "Selenium is not installed/available"

```bash
pip install selenium>=4.36.0
pip install webdriver-manager>=4.0.2
```

### 2. "Failed to setup Chrome driver"

```bash
# Install Chrome or Chromium
sudo apt-get install chromium-browser
# or
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

### 3. "Navigation failed: ERR_NAME_NOT_RESOLVED"

- Check internet connection
- Verify the URL is accessible
- Try from a different network/IP

### 4. Persistent Anti-Bot Blocking

1. **Try different networks**: Use residential IP instead of datacenter/VPS
2. **Manual browser test**: Access the site manually first
3. **Longer delays**: Increase delays between requests
4. **Different timing**: Run during off-peak hours

## Performance Tips

### Optimal Settings for Different Protection Levels:

**Light Protection (Generic anti-bot)**:
- Default settings work well
- 5-15 second delays

**Medium Protection (Cloudflare)**:
- Enable all retry strategies  
- 15-30 second delays
- Manual browser access first

**Heavy Protection (Incapsula/DataDome)**:
- Residential IP addresses required
- 30-60 second delays minimum
- Multiple retry attempts
- Geographic location variations

### Success Indicators:

✅ **Good signs**:
```
Applied realistic request headers via CDP
Browser driver ready  
Navigation successful
Found X products using selector: Y
```

❌ **Warning signs**:
```
Protection type: Incapsula
All fallback strategies exhausted
ERROR: Unable to bypass X protection
```

## Integration with Other Tools

### With Notification Service:
```python
from scraper_intl import InternationalETBScraper
from notification_service import create_notification_service

scraper = InternationalETBScraper()
products = scraper.scrape_products()

if products:
    notification_service = create_notification_service()
    notification_service.notify_products(products)
```

### Scheduled Running:
```bash
# Run every hour with enhanced logging
0 * * * * cd /path/to/scraper && python3 scraper_intl.py >> scraper.log 2>&1
```

## Monitoring and Metrics

The enhanced scraper provides detailed metrics:

- **Success rate**: Percentage of successful scrapes
- **Protection detection**: Types and frequency  
- **Retry effectiveness**: Which strategies work best
- **Performance timing**: Page load and processing times

Monitor these metrics to optimize performance for your specific use case.