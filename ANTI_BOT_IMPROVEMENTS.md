# Anti-Bot Protection Improvements for ETB Scraper

## Overview

This document describes the comprehensive enhancements made to the international ETB scraper to bypass advanced anti-bot protection systems, particularly Incapsula protection detected on Pokemon Center.

## Problem Analysis

The original issue showed:
- Scraper detected Incapsula protection: "Blocked by Incapsula protection"
- Page loaded with minimal content (1088 characters, empty title)
- Standard retry strategies were insufficient

## Enhanced Features

### 1. User Agent Rotation System

**Before**: Fixed user agent string
```python
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0'
```

**After**: Dynamic rotation from 5 realistic user agents
```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.7339.207 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139.0.6931.134 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0.7339.207 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0'
]
```

### 2. Enhanced Chrome Options

Added **21 new Chrome arguments** for better stealth:

**Anti-Detection Arguments**:
- `--disable-blink-features=AutomationControlled`
- `--disable-client-side-phishing-detection`
- `--disable-background-timer-throttling`
- `--disable-backgrounding-occluded-windows`
- `--disable-renderer-backgrounding`
- `--disable-field-trial-config`
- `--disable-ipc-flooding-protection`

**Natural Behavior Arguments**:
- `--enable-features=NetworkService`
- `--force-device-scale-factor=1`
- `--simulate-outdated-no-au="Tue, 31 Dec 2099 23:59:59 GMT"`

**Randomized Window Sizes**:
```python
window_sizes = ['1920,1080', '1366,768', '1536,864', '1440,900', '1600,900']
```

### 3. Advanced JavaScript Anti-Detection

**Navigator Property Overrides**:
- Hide `navigator.webdriver` property completely
- Mock realistic `navigator.plugins` with actual plugin objects
- Set realistic `hardwareConcurrency` (4 cores)
- Override `deviceMemory` to 8GB
- Set platform-specific properties

**Enhanced Browser Fingerprint**:
```javascript
// Realistic WebGL parameters
if (parameter === 37445) return 'Intel Inc.';
if (parameter === 37446) return 'Intel(R) HD Graphics 620';

// Realistic screen properties
Object.defineProperty(screen, 'availWidth', {get: () => 1920});
Object.defineProperty(screen, 'availHeight', {get: () => 1040});

// Mock battery API
navigator.getBattery = () => Promise.resolve({
    charging: true, level: 1, chargingTime: 0
});
```

### 4. Chrome DevTools Protocol (CDP) Integration

Added realistic request headers via CDP:
```python
self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
    "userAgent": self.current_user_agent,
    "acceptLanguage": "en-US,en;q=0.9",
    "platform": "Win32"
})
```

### 5. Enhanced Retry Strategies

**Before**: 3 basic retry strategies
**After**: 5 sophisticated strategies with progressive backoff

1. **Progressive Delay**: 15s → 30s → 45s waits with cache clearing
2. **Enhanced Cookie Clearing**: Complete browser state reset
3. **Human Behavior Simulation**: Homepage navigation + scrolling
4. **Long Wait and Reload**: Extended delays
5. **Random Delay Retry**: Randomized timing

### 6. Improved Protection Detection

**Enhanced Detection for Multiple Systems**:

| System | Indicators | Count |
|--------|------------|-------|
| Incapsula | `incapsula incident id`, `_incap_sys_visid_`, `__incap` | 5 |
| Cloudflare | `cf-ray`, `__cf_bm`, `just a moment` | 10 |
| DataDome | `datadome`, `_dd_s`, `dd_captcha` | 4 |
| PerimeterX | `_px`, `perimeterx`, `px-captcha` | 4 |
| Generic | `access denied`, `captcha`, `verify you are human` | 12 |

### 7. Protection-Specific Guidance

Added intelligent troubleshooting based on detected protection:

**Incapsula Guidance**:
- Use residential IP addresses
- Implement 30-60 second delays
- Rotate browser fingerprints
- Try different geographic locations

**Cloudflare Guidance**:
- Wait for JavaScript challenges
- Avoid concurrent requests
- Maintain realistic timing

**DataDome Guidance**:
- Implement mouse movements
- Use very human-like patterns
- Rotate IPs frequently

### 8. Human-Like Timing

**Before**: Fixed 5-second delays
**After**: Randomized, realistic timing
```python
initial_wait = random.uniform(8, 12)  # 8-12 second range
delay = random.uniform(5, 15)         # Variable delays
```

### 9. Enhanced Error Handling

Added specific error type detection and guidance:
- `ERR_NAME_NOT_RESOLVED` → DNS/Network issues
- `ERR_CONNECTION_TIMED_OUT` → Timeout guidance
- `ERR_INTERNET_DISCONNECTED` → Connection problems

## Testing Results

All enhancements validated through comprehensive testing:

✅ **User agent rotation** (5 agents)  
✅ **Chrome options** (33 arguments)  
✅ **Anti-detection JavaScript** (navigator.webdriver hidden)  
✅ **Protection detection** (4 systems, 35+ indicators)  
✅ **Retry strategies** (5 different approaches)  
✅ **CDP integration** (realistic headers)  

## Usage

The enhanced scraper automatically applies all improvements:

```python
from scraper_intl import InternationalETBScraper

# All enhancements applied automatically
scraper = InternationalETBScraper("https://www.pokemoncenter.com/category/elite-trainer-box")
products = scraper.scrape_products()
```

## Expected Results

With these enhancements, the scraper should:

1. **Bypass Incapsula protection** more effectively
2. **Appear more human-like** to detection systems
3. **Recover gracefully** when temporarily blocked
4. **Provide better guidance** when protection is detected
5. **Maintain higher success rates** over time

## Monitoring

The scraper now provides detailed logging for:
- Protection type detection
- Retry strategy success/failure
- Anti-detection measure application
- Performance metrics

This allows for continuous improvement and optimization based on real-world results.