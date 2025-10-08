#!/usr/bin/env python3
"""
Test script to validate the new Buy Now flow functionality.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_components.core.availability_checker import AvailabilityChecker
from scraper_components.config.constants import BUY_NOW_SELECTORS

def test_buy_now_selectors():
    """Test that buy now selectors are properly defined."""
    print("Testing BUY_NOW_SELECTORS...")
    assert len(BUY_NOW_SELECTORS) > 0, "BUY_NOW_SELECTORS should not be empty"
    print(f"✓ Found {len(BUY_NOW_SELECTORS)} buy now selectors")
    
    # Check for expected selector types
    has_data_qa = any('data-qa' in selector for selector in BUY_NOW_SELECTORS)
    has_class_based = any('class*=' in selector for selector in BUY_NOW_SELECTORS)
    has_testid = any('data-testid' in selector for selector in BUY_NOW_SELECTORS)
    
    print(f"✓ Has data-qa selectors: {has_data_qa}")
    print(f"✓ Has class-based selectors: {has_class_based}")
    print(f"✓ Has data-testid selectors: {has_testid}")

def test_availability_checker_methods():
    """Test that AvailabilityChecker has the new method."""
    print("\nTesting AvailabilityChecker methods...")
    
    # Create mock objects
    mock_driver = Mock()
    mock_page_validator = Mock()
    mock_product_extractor = Mock()
    mock_webdriver_manager = Mock()
    
    # Create AvailabilityChecker instance
    checker = AvailabilityChecker(
        driver=mock_driver,
        page_validator=mock_page_validator,
        product_extractor=mock_product_extractor,
        webdriver_manager=mock_webdriver_manager
    )
    
    # Check that the new method exists
    assert hasattr(checker, 'click_buy_now_button'), "click_buy_now_button method should exist"
    print("✓ click_buy_now_button method exists")
    
    # Check that helper method exists
    assert hasattr(checker, '_find_buy_now_button'), "_find_buy_now_button method should exist"
    print("✓ _find_buy_now_button helper method exists")

def test_scraper_old_import():
    """Test that scraper_old can be imported with the modifications."""
    print("\nTesting scraper_old import...")
    try:
        import scraper_old
        print("✓ scraper_old imports successfully")
        
        # Check that main function exists
        assert hasattr(scraper_old, 'main'), "main function should exist"
        print("✓ main function exists")
        
    except Exception as e:
        print(f"✗ Error importing scraper_old: {e}")
        raise

def test_mock_buy_now_flow():
    """Test the buy now flow with mocked components."""
    print("\nTesting mock buy now flow...")
    
    # Create mock objects
    mock_driver = Mock()
    mock_page_validator = Mock()
    mock_webdriver_manager = Mock()
    
    # Mock successful page validation
    mock_page_validator.wait_for_page_ready.return_value = True
    
    # Create AvailabilityChecker instance
    checker = AvailabilityChecker(
        driver=mock_driver,
        page_validator=mock_page_validator,
        webdriver_manager=mock_webdriver_manager
    )
    
    # Test with invalid URL
    success, message = checker.click_buy_now_button("invalid-url")
    assert not success, "Should fail with invalid URL"
    assert "Invalid URL" in message, f"Expected 'Invalid URL' in message, got: {message}"
    print("✓ Properly handles invalid URL")
    
    # Test with valid URL but no button found (mock scenario)
    with patch.object(checker, '_find_buy_now_button', return_value=None):
        success, message = checker.click_buy_now_button("https://example.com/product")
        assert not success, "Should fail when no button found"
        assert "No buy now button found" in message, f"Expected 'No buy now button found' in message, got: {message}"
        print("✓ Properly handles missing buy button")

if __name__ == "__main__":
    print("Running Buy Now Flow Tests")
    print("=" * 50)
    
    try:
        test_buy_now_selectors()
        test_availability_checker_methods()
        test_scraper_old_import()
        test_mock_buy_now_flow()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)