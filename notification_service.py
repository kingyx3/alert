#!/usr/bin/env python3

"""
Notification Service Module
Handles Telegram bot messaging to a specified channel
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    import telebot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Telegram Bot API not available. Please install pytelegrambotapi package.")


class NotificationService:
    """Service class for handling Telegram channel notifications"""
    
    def __init__(self, telegram_bot_token=None, telegram_channel_id=None):
        """
        Initialize the notification service
        
        Args:
            telegram_bot_token (str): Telegram Bot API token
            telegram_channel_id (str): Telegram Channel ID to send notifications to
        """
        self.telegram_bot = None
        self.telegram_channel_id = None
        self.telegram_initialized = False
        
        # Try to initialize Telegram
        if TELEGRAM_AVAILABLE:
            self._init_telegram(telegram_bot_token, telegram_channel_id)
    
    def _init_telegram(self, bot_token=None, channel_id=None):
        """Initialize Telegram Bot"""
        try:
            bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
            channel_id = channel_id or os.getenv('TELEGRAM_CHANNEL_ID')
            
            if not bot_token:
                print(f"[{datetime.now()}] Telegram bot token not provided. Set TELEGRAM_BOT_TOKEN environment variable.")
                return
                
            if not channel_id:
                print(f"[{datetime.now()}] Telegram channel ID not provided. Set TELEGRAM_CHANNEL_ID environment variable.")
                return
            
            self.telegram_bot = telebot.TeleBot(bot_token)
            self.telegram_channel_id = channel_id
            self.telegram_initialized = True
            print(f"[{datetime.now()}] Telegram bot initialized successfully for channel: {channel_id}")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error initializing Telegram bot: {str(e)}")

    
    def format_products_text(self, products: List[Dict[str, Any]]) -> str:
        """
        Format the scraped products into a single text message
        
        Args:
            products (List[Dict]): List of product dictionaries from scraper2 format
            
        Returns:
            str: Formatted text string
        """
        if not products:
            return "🚫 No available products found at this time."
        
        # Sort products alphabetically by name
        sorted_products = sorted(products, key=lambda x: x.get('name', '').lower())
        
        header = f"🛒 Store Alert - {(datetime.now()+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}\n"
        header += f"📦 Found {len(sorted_products)} available products:\n\n"
        
        product_lines = []
        for idx, product in enumerate(sorted_products, 1):
            # Use scraper2 field names
            name = product.get('name', 'Unknown Product')
            url = product.get('url', '')
            
            # Get price information - try priceShow first, then calculate from price
            price_show = product.get('priceShow', 'N/A')
            if not price_show and 'price' in product and product['price'] is not None:
                price_show = f"${product['price']:.2f}"
            
            # Get sold count information
            sold = product.get('sold', '')
            sold_text = f' - "{sold}"' if sold else ''
            
            product_line = f"{idx}. 🎯 {name} ({price_show}){sold_text}\n"
            product_line += f"   🔗 {url}\n"
            product_lines.append(product_line)
        
        return header + "\n".join(product_lines)
    
    def send_to_telegram_channel(self, message: str) -> bool:
        """
        Send message to the configured Telegram channel
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        if not self.telegram_initialized:
            print(f"[{datetime.now()}] Telegram not initialized. Cannot send messages.")
            return False
        
        try:
            # Split long messages if needed (Telegram has a 4096 character limit)
            if len(message) > 4000:
                # Split message into chunks
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        self.telegram_bot.send_message(self.telegram_channel_id, chunk)
                    else:
                        self.telegram_bot.send_message(self.telegram_channel_id, f"...continued\n{chunk}")
            else:
                self.telegram_bot.send_message(self.telegram_channel_id, message)
            
            print(f"[{datetime.now()}] Successfully sent message to channel: {self.telegram_channel_id}")
            return True
            
        except Exception as e:
            print(f"[{datetime.now()}] Failed to send message to channel {self.telegram_channel_id}: {str(e)}")
            return False
    
    def notify_products(self, products: List[Dict[str, Any]]) -> bool:
        """
        Complete notification workflow: format message and send to channel
        
        Args:
            products (List[Dict]): List of scraped products
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            if not self.telegram_initialized:
                print(f"[{datetime.now()}] Telegram not initialized. Cannot send notification.")
                return False
            
            # Format products into text message
            message = self.format_products_text(products)
            
            # Send to configured channel
            success = self.send_to_telegram_channel(message)
            
            if success:
                print(f"[{datetime.now()}] Product notification sent successfully to channel")
            else:
                print(f"[{datetime.now()}] Failed to send product notification")
            
            return success
            
        except Exception as e:
            print(f"[{datetime.now()}] Error in notification workflow: {str(e)}")
            return False


# Convenience function for easy integration
def create_notification_service():
    """Create a notification service with environment variables"""
    return NotificationService()
