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

    
    def format_products_text(self, products: List[Dict[str, Any]], total_count: int = None, sold_count: int = None) -> str:
        """
        Format the scraped products into a single text message
        
        Args:
            products (List[Dict]): List of product dictionaries
            total_count (int): Total number of products checked
            sold_count (int): Number of products sold out
            
        Returns:
            str: Formatted text string
        """
        if not products:
            message = "🚫 No available products found at this time."
            if sold_count is not None and sold_count > 0:
                message += f"\n💔 {sold_count} products sold out as of scraping time."
            return message
        
        header = f"🛒 Store Alert - {(datetime.now()+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}\n"
        header += f"📦 Found {len(products)} available products"
        if total_count is not None:
            header += f" out of {total_count} checked"
        if sold_count is not None and sold_count > 0:
            header += f"\n💔 {sold_count} products sold out as of scraping time"
        header += ":\n\n"
        
        product_lines = []
        for idx, product in enumerate(products, 1):
            title = product.get('title', 'Unknown Product')
            url = product.get('url', '')
            status = product.get('availability_status', 'Status unknown')
            price = product.get('price', '')
            
            product_line = f"{idx}. 🎯 {title} ({price})\n"
            # if price:
            #     product_line += f"   💰 {price}\n"
            product_line += f"   🔗 {url}\n"
            # product_line += f"   ✅ {status}\n"
            
            product_lines.append(product_line)
        
        # footer = f"\n🤖 Automated scraping completed at {datetime.now().strftime('%H:%M:%S')}"
        
        return header + "\n".join(product_lines) # + footer
    
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
    
    def notify_products(self, products: List[Dict[str, Any]], total_count: int = None, sold_count: int = None) -> bool:
        """
        Complete notification workflow: format message and send to channel
        
        Args:
            products (List[Dict]): List of scraped products
            total_count (int): Total number of products checked
            sold_count (int): Number of products sold out
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            if not self.telegram_initialized:
                print(f"[{datetime.now()}] Telegram not initialized. Cannot send notification.")
                return False
            
            # Format products into text message
            message = self.format_products_text(products, total_count, sold_count)
            
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