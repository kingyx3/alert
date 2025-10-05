#!/usr/bin/env python3
"""
Integration test to validate the fix for issue #22 works end-to-end.
"""

from unittest.mock import Mock
from scraper_components.core.availability_checker import AvailabilityChecker
from scraper_components.config.constants import BUY_INDICATORS

def test_fix_integration():
    """Test that the fix resolves the original issue."""
    
    print("=== Issue #22 Fix Validation ===")
    print(f"Updated BUY_INDICATORS: {BUY_INDICATORS}")
    print(f"Total indicators: {len(BUY_INDICATORS)}")
    
    # Create mock driver
    mock_driver = Mock()
    mock_page_validator = Mock()
    checker = AvailabilityChecker(mock_driver, mock_page_validator)
    
    # Test scenarios that would have failed before the fix
    test_scenarios = [
        ('<button>Add to Cart</button>', "Add to Cart button"),
        ('<button>Purchase Now</button>', "Purchase button"), 
        ('<a href="/cart">Buy</a>', "Generic Buy link"),
        ('<input type="submit" value="Order">', "Order button"),
        ('<button class="checkout-btn">Checkout</button>', "Checkout button"),
    ]
    
    print("\n=== Testing availability detection ===")
    
    all_passed = True
    for page_content, description in test_scenarios:
        mock_driver.page_source = page_content
        is_available, reason = checker.check_availability_indicators()
        
        status = "✅ PASS" if is_available else "❌ FAIL"
        print(f"{status}: {description}")
        print(f"   Content: {page_content}")
        print(f"   Result: {is_available} - {reason}")
        
        if not is_available:
            all_passed = False
    
    print(f"\n=== Overall Result ===")
    if all_passed:
        print("✅ All scenarios PASSED - Issue #22 is FIXED!")
        print("The system now correctly detects availability with various purchase button texts.")
    else:
        print("❌ Some scenarios FAILED - Issue #22 is NOT fully fixed.")
    
    return all_passed

if __name__ == '__main__':
    test_fix_integration()