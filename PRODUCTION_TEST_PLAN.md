# Production Testing Plan

## Test Cases for Live Environment

When deploying the enhanced scraper to an environment with full network access, follow this test plan:

### 1. Basic Functionality Test

```bash
export SCRAPING_URL_INTL_ETB="https://www.pokemoncenter.com/category/elite-trainer-box"
python3 scraper_intl.py
```

**Expected Results:**
- ✅ Chrome driver setup successful
- ✅ "Applied realistic request headers via CDP" message
- ✅ Random user agent selection logged
- ✅ Navigation successful (or protection detected with retry attempts)

### 2. Protection Bypass Test

If Incapsula protection is encountered:

**Look for these log messages:**
```
[timestamp] === ANTI-BOT PROTECTION DETECTED ===
[timestamp] Protection type: Incapsula
[timestamp] Attempting to bypass Incapsula protection...
[timestamp] Trying strategy: Progressive delay with navigation
```

**Success indicators:**
- ✅ Multiple retry strategies attempted
- ✅ "SUCCESS: [strategy] worked" message
- ✅ Page content increases significantly after retry
- ✅ Products found and extracted

### 3. Anti-Detection Validation

Test that stealth measures are working:

```python
from scraper_intl import ETBWebDriverManager

manager = ETBWebDriverManager()
manager.setup_driver()
manager.driver.get("https://www.pokemoncenter.com")

# These should return expected values
print("webdriver hidden:", manager.driver.execute_script("return navigator.webdriver"))  # Should be None/undefined
print("plugins count:", manager.driver.execute_script("return navigator.plugins.length"))  # Should be 3
print("user agent:", manager.driver.execute_script("return navigator.userAgent"))  # Should match selected UA

manager.quit_driver()
```

### 4. Performance Benchmarks

Monitor these metrics over multiple runs:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Initial page load | < 15 seconds | Time to navigation success |
| Protection bypass | < 3 minutes | Time to bypass if blocked |
| Product extraction | < 30 seconds | Time to find products |
| Overall success rate | > 80% | Successful scrapes / total attempts |

### 5. Error Handling Test

Intentionally test error conditions:

**Network Issues:**
```bash
# Test with invalid URL
SCRAPING_URL_INTL_ETB="https://invalid-site.com" python3 scraper_intl.py
```
Expected: Proper error handling and troubleshooting guidance

**Rate Limiting:**
```bash
# Run multiple times quickly
for i in {1..3}; do python3 scraper_intl.py & done
```
Expected: Graceful handling and retry suggestions

### 6. Comparison Test

**Before Enhancement:**
- Save a baseline of current behavior
- Note: Protection detection, bypass success rate, timing

**After Enhancement:**
- Compare success rates
- Measure improvement in bypass effectiveness
- Document any remaining issues

### 7. Long-term Monitoring

Set up monitoring for:

**Daily Metrics:**
- Success rate percentage
- Average response time
- Protection types encountered
- Most effective retry strategies

**Weekly Analysis:**
- Trends in protection detection
- Strategy effectiveness over time
- Need for additional user agents or techniques

### 8. Troubleshooting Scenarios

**If still blocked after all retries:**

1. **Check IP reputation:**
   ```bash
   curl -s https://whatismyipaddress.com/blacklist-check
   ```

2. **Test from different network:**
   - Try residential IP vs datacenter IP
   - Test from different geographic locations
   - Use mobile network vs broadband

3. **Manual browser test:**
   - Access site manually in browser first
   - Complete any manual challenges
   - Then retry scraper

4. **Adjust timing:**
   - Increase delays in retry strategies
   - Run during off-peak hours
   - Reduce request frequency

### 9. Success Metrics

**Immediate Success (Within 1 day):**
- ✅ Scraper bypasses Incapsula protection
- ✅ Products are successfully extracted
- ✅ No manual intervention required

**Short-term Success (Within 1 week):**
- ✅ Consistent success rate > 80%
- ✅ Stable performance over multiple runs
- ✅ Effective protection bypass strategies identified

**Long-term Success (Within 1 month):**
- ✅ Sustained performance without degradation
- ✅ Adaptation to any protection system changes
- ✅ Optimized timing and strategy selection

### 10. Documentation Updates

Based on production testing results:

1. **Update timing parameters** if needed
2. **Add new user agents** if current ones become detected
3. **Refine retry strategies** based on success rates
4. **Document site-specific optimizations**

### Emergency Rollback Plan

If enhanced scraper performs worse than original:

1. **Revert to original scraper_intl.py**
2. **Keep enhanced detection and logging**
3. **Gradually re-introduce improvements**
4. **Test individual enhancements separately**

---

**Note**: This comprehensive solution addresses the core issue of Incapsula protection blocking the Pokemon Center ETB scraper. The enhancements provide multiple layers of protection bypass capabilities while maintaining compatibility with existing functionality.