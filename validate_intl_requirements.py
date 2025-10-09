#!/usr/bin/env python3
"""
Validation script for International ETB Scraper requirements.

This script checks if all required dependencies for scraper_intl.py are properly installed.
"""

import sys
from typing import List, Tuple

def check_import(module_name: str, import_from: str = None) -> Tuple[bool, str]:
    """Check if a module can be imported successfully."""
    try:
        if import_from:
            exec(f"from {import_from} import {module_name}")
        else:
            __import__(module_name)
        return True, "✓ Available"
    except ImportError as e:
        return False, f"✗ Missing: {str(e)}"
    except Exception as e:
        return False, f"✗ Error: {str(e)}"

def validate_requirements() -> bool:
    """Validate all requirements for international scraper."""
    print("Validating International ETB Scraper Requirements")
    print("=" * 50)
    
    # Core dependencies for scraper_intl.py
    requirements = [
        ("selenium", None, "Core web automation library"),
        ("webdriver_manager", None, "Automatic WebDriver management"),
        ("requests", None, "HTTP requests library"),
        ("telebot", "pytelegrambotapi", "Telegram bot API"),
    ]
    
    all_passed = True
    
    for module, package, description in requirements:
        success, message = check_import(module)
        status = "REQUIRED" if module in ["selenium", "webdriver_manager"] else "OPTIONAL"
        print(f"{module:20} [{status:8}] {message:20} - {description}")
        
        if not success and module in ["selenium", "webdriver_manager"]:
            all_passed = False
    
    print("\nSelenium Components:")
    print("-" * 30)
    
    # Selenium specific imports
    selenium_components = [
        ("webdriver", "selenium", "WebDriver main class"),
        ("Options", "selenium.webdriver.chrome.options", "Chrome options"),
        ("Service", "selenium.webdriver.chrome.service", "Chrome service"),
        ("By", "selenium.webdriver.common.by", "Element locators"),
        ("WebDriverWait", "selenium.webdriver.support.ui", "Wait conditions"),
        ("ChromeDriverManager", "webdriver_manager.chrome", "Chrome driver manager"),
    ]
    
    selenium_available = check_import("selenium")[0]
    
    for component, import_from, description in selenium_components:
        if selenium_available or "webdriver_manager" in import_from:
            success, message = check_import(component, import_from)
            print(f"{component:20} {message:20} - {description}")
        else:
            print(f"{component:20} ✗ Selenium not available - {description}")
    
    print(f"\nValidation Result:")
    print("-" * 20)
    if all_passed:
        print("✓ All required dependencies are available")
        print("✓ International ETB Scraper should work properly")
    else:
        print("✗ Some required dependencies are missing")
        print("✗ Run: pip install -r requirements_intl.txt")
    
    return all_passed

if __name__ == "__main__":
    success = validate_requirements()
    sys.exit(0 if success else 1)