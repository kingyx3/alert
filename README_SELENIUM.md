# Selenium Automation for Buy Button Clicking

This document explains the selenium automation feature that automatically attempts to purchase available products by clicking "buy now" buttons.

## Overview

When the scraper finds available products, it can now automatically navigate to each product page and attempt to click the buy button using Selenium WebDriver. This feature includes comprehensive debugging through screenshots and detailed logging.

## Features

### 🔍 Smart Buy Button Detection
- **Multiple CSS Selectors**: Tries various common buy button selectors
- **Text-Based Search**: Searches for buttons containing "Buy Now", "Add to Cart", etc.
- **Multi-Language Support**: Includes Chinese text patterns for international sites
- **Visibility Checks**: Only clicks visible and enabled buttons

### 📸 Screenshot Debugging
Screenshots are automatically captured at key points:
- **Initial Page Load**: Before any interaction
- **Button Found**: When a buy button is detected
- **Before Click**: Right before clicking the button
- **After Click**: After clicking to see the result
- **Errors**: When timeouts or errors occur
- **No Button Found**: When no buy button is detected

All screenshots are timestamped and include product names for easy identification.

### 🚀 GitHub Actions Integration
- **Chrome Installation**: Automatically installs Chrome in CI environment
- **Headless Mode**: Runs browser without GUI for CI compatibility
- **Artifact Upload**: Screenshots and results are saved as GitHub Actions artifacts
- **Retention**: Artifacts are kept for 30 days for debugging

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISABLE_SELENIUM_AUTOMATION` | Set to `true` to disable automation | `false` |

### GitHub Actions Secrets/Variables
- All existing secrets (TELEGRAM_BOT_TOKEN, etc.) work as before
- Add `DISABLE_SELENIUM_AUTOMATION` as a repository variable if needed

## Usage

### Automatic Integration
The selenium automation is automatically triggered when:
1. The scraper finds available products
2. Selenium is available (installed)
3. Automation is not disabled via environment variable

### Manual Testing
```bash
# Test with sample data
python selenium_automation.py

# Test complete workflow
python -c "
import selenium_automation
products = [{'name': 'Test', 'url': 'https://example.com', 'inStock': True}]
results = selenium_automation.automate_purchases(products, headless=False)
print(results)
"
```

### Disable Automation
```bash
# Disable via environment variable
export DISABLE_SELENIUM_AUTOMATION=true
python scraper.py

# Or in GitHub Actions, set the DISABLE_SELENIUM_AUTOMATION variable
```

## File Structure

```
├── selenium_automation.py     # Main automation module
├── screenshots/              # Debug screenshots (git-ignored)
├── automation_results_*.json # Results summary (git-ignored)
└── .github/workflows/scraper.yml # Updated workflow
```

## Buy Button Selectors

The automation tries these selectors in order:
1. `button[data-spm-click*='buy']` - Lazada specific
2. `button:contains('Buy Now')` - Generic text search
3. `.add-to-cart-btn` - Common CSS class
4. `.buy-now-btn` - Common CSS class
5. `[data-testid='buy-button']` - Test ID selector
6. `.pdp-button-colour--orange` - Lazada specific
7. Text-based search for multiple languages

## Results Format

The automation returns detailed results:
```json
{
  "selenium_available": true,
  "total_products": 3,
  "attempted": 3,
  "successful": 2,
  "failed": 1,
  "details": [
    {
      "product": "Product Name",
      "success": true,
      "url": "https://example.com/product"
    }
  ]
}
```

## Error Handling

- **Selenium Not Available**: Graceful fallback with warning message
- **WebDriver Failures**: Detailed error logging and screenshots
- **Timeout Issues**: Configurable timeouts with debug screenshots
- **Missing URLs**: Products without URLs are skipped with logging

## Security Considerations

- **Headless Mode**: Reduces resource usage and improves security
- **No Personal Data**: No passwords or payment information is stored
- **Click Only**: Only clicks buttons, doesn't fill forms or complete purchases
- **Rate Limiting**: Small delays between product attempts

## Troubleshooting

### Common Issues

1. **"Selenium not available"**
   - Install with: `pip install selenium webdriver-manager`

2. **"WebDriver failed to initialize"**
   - Ensure Chrome is installed
   - Check Chrome and ChromeDriver compatibility

3. **"No buy button found"**
   - Check screenshots in artifacts
   - Product page might have changed structure
   - Button might be behind login/captcha

4. **Timeout errors**
   - Network issues or slow loading pages
   - Check screenshots for page state
   - Consider increasing DEFAULT_TIMEOUT

### Debug Information

- **Screenshots**: Check GitHub Actions artifacts
- **Logs**: All actions are logged with timestamps
- **Results JSON**: Detailed success/failure information
- **Console Output**: Real-time progress updates

## Limitations

- Only clicks buttons, doesn't complete full purchase flow
- May not work with sites requiring login
- Could be blocked by anti-bot measures
- Success depends on page structure consistency

## Future Enhancements

- Support for login flows
- Captcha handling
- More sophisticated bot detection avoidance
- Custom selector configuration
- Purchase flow completion