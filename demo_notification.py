#!/usr/bin/env python3

"""
Demo script for notification service functionality
This demonstrates the integration without requiring actual Firebase/Telegram setup
"""

from unittest.mock import patch, MagicMock
from datetime import datetime
import json

def demo_notification_service():
    """Demo the notification service with mock data"""
    print(f"[{datetime.now()}] Demo: Notification Service Integration")
    print("="*80)
    
    # Mock product data (similar to scraper output)
    mock_products = [
        {
            'title': 'Pokemon Premium Card Pack',
            'price': '$29.99',
            'url': 'https://www.lazada.sg/product/premium-pack',
            'image': 'https://example.com/image1.jpg',
            'availability_status': 'Available - Buy Now button found',
            'is_available': True,
            'scraped_at': datetime.now().isoformat()
        },
        {
            'title': 'Pokemon Standard Edition Deck',
            'price': '$19.99', 
            'url': 'https://www.lazada.sg/product/standard-deck',
            'image': 'https://example.com/image2.jpg',
            'availability_status': 'Available - Buy Now button found',
            'is_available': True,
            'scraped_at': datetime.now().isoformat()
        }
    ]
    
    # Import the notification service
    from notification_service import NotificationService
    
    # Create mock Telegram service
    with patch('telebot.TeleBot') as mock_telegram_bot:
        
        # Mock Telegram bot
        mock_bot_instance = MagicMock()
        mock_telegram_bot.return_value = mock_bot_instance
        
        # Create notification service
        notification_service = NotificationService(
            telegram_bot_token='mock_telegram_bot_token',
            telegram_channel_id='-1001234567890'
        )
        
        # Force initialization for demo
        notification_service.telegram_initialized = True
        notification_service.telegram_channel_id = '-1001234567890'
        
        print(f"[{datetime.now()}] Mock services initialized")
        
        # Demo: Format products text
        formatted_text = notification_service.format_products_text(mock_products)
        print(f"[{datetime.now()}] Formatted notification text:")
        print("-" * 50)
        print(formatted_text)
        print("-" * 50)
        
        # Demo: Send notification to channel (mocked)
        success = notification_service.send_to_telegram_channel(formatted_text)
        print(f"[{datetime.now()}] Channel notification result: {success}")
        
        # Demo: Complete workflow
        success = notification_service.notify_products(mock_products)
        print(f"[{datetime.now()}] Complete notification workflow success: {success}")
        
        # Show what would be sent to Telegram
        print(f"\n[{datetime.now()}] Mock Telegram bot calls:")
        for call in mock_bot_instance.send_message.call_args_list:
            channel_id, message = call[0]
            print(f"  -> Channel ID {channel_id}: {len(message)} characters")


def demo_text_formatting():
    """Demo just the text formatting functionality"""
    print(f"\n[{datetime.now()}] Demo: Text Formatting Only")
    print("="*80)
    
    from notification_service import NotificationService
    
    # Create service without initialization for text formatting only
    service = NotificationService()
    
    # Sample products
    products = [
        {
            'title': 'Pokemon Booster Pack - Scarlet & Violet',
            'price': 'S$8.90',
            'url': 'https://www.lazada.sg/products/booster-pack-sv',
            'availability_status': 'In Stock - Ready to ship'
        },
        {
            'title': 'Pokemon Trading Card Game Battle Academy',
            'price': 'S$35.50', 
            'url': 'https://www.lazada.sg/products/battle-academy',
            'availability_status': 'Available - Buy Now button found'
        }
    ]
    
    formatted_text = service.format_products_text(products)
    print("Formatted notification message:")
    print("="*50)
    print(formatted_text)
    print("="*50)
    
    # Test with no products
    empty_text = service.format_products_text([])
    print("\nFormatted message for no products:")
    print("="*50)
    print(empty_text)
    print("="*50)


if __name__ == "__main__":
    demo_notification_service()
    demo_text_formatting()