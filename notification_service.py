#!/usr/bin/env python3

"""
Notification Service Module
Handles Firebase RTDB integration and Telegram bot messaging
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Firebase Admin SDK not available. Please install firebase-admin package.")

try:
    import telebot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Telegram Bot API not available. Please install pytelegrambotapi package.")


class NotificationService:
    """Service class for handling Firebase RTDB and Telegram notifications"""
    
    def __init__(self, firebase_service_account_path=None, firebase_database_url=None, telegram_bot_token=None):
        """
        Initialize the notification service
        
        Args:
            firebase_service_account_path (str): Path to Firebase service account JSON file
            firebase_database_url (str): Firebase Realtime Database URL
            telegram_bot_token (str): Telegram Bot API token
        """
        self.firebase_app = None
        self.telegram_bot = None
        self.firebase_initialized = False
        self.telegram_initialized = False
        
        # Try to initialize Firebase
        if FIREBASE_AVAILABLE:
            self._init_firebase(firebase_service_account_path, firebase_database_url)
        
        # Try to initialize Telegram
        if TELEGRAM_AVAILABLE:
            self._init_telegram(telegram_bot_token)
    
    def _init_firebase(self, service_account_path=None, database_url=None):
        """Initialize Firebase Admin SDK"""
        try:
            # Use environment variables as fallback
            service_account_path = service_account_path or os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
            database_url = database_url or os.getenv('FIREBASE_DATABASE_URL')
            
            if not service_account_path or not database_url:
                print(f"[{datetime.now()}] Firebase credentials not provided. Set FIREBASE_SERVICE_ACCOUNT_PATH and FIREBASE_DATABASE_URL environment variables.")
                return
            
            if not os.path.exists(service_account_path):
                print(f"[{datetime.now()}] Firebase service account file not found: {service_account_path}")
                return
            
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                self.firebase_app = firebase_admin.initialize_app(cred, {
                    'databaseURL': database_url
                })
            else:
                self.firebase_app = firebase_admin.get_app()
            
            self.firebase_initialized = True
            print(f"[{datetime.now()}] Firebase initialized successfully")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error initializing Firebase: {str(e)}")
    
    def _init_telegram(self, bot_token=None):
        """Initialize Telegram Bot"""
        try:
            bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
            
            if not bot_token:
                print(f"[{datetime.now()}] Telegram bot token not provided. Set TELEGRAM_BOT_TOKEN environment variable.")
                return
            
            self.telegram_bot = telebot.TeleBot(bot_token)
            self.telegram_initialized = True
            print(f"[{datetime.now()}] Telegram bot initialized successfully")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error initializing Telegram bot: {str(e)}")
    
    def get_chat_ids_from_firebase(self, path='/telegram_chat_ids') -> List[str]:
        """
        Fetch list of Telegram chat IDs from Firebase RTDB
        
        Args:
            path (str): Path in Firebase RTDB where chat IDs are stored
            
        Returns:
            List[str]: List of chat IDs
        """
        if not self.firebase_initialized:
            print(f"[{datetime.now()}] Firebase not initialized. Cannot fetch chat IDs.")
            return []
        
        try:
            ref = db.reference(path)
            data = ref.get()
            
            if data is None:
                print(f"[{datetime.now()}] No chat IDs found at path: {path}")
                return []
            
            # Handle different data structures
            chat_ids = []
            if isinstance(data, list):
                chat_ids = [str(chat_id) for chat_id in data if chat_id]
            elif isinstance(data, dict):
                chat_ids = [str(chat_id) for chat_id in data.values() if chat_id]
            else:
                chat_ids = [str(data)]
            
            print(f"[{datetime.now()}] Retrieved {len(chat_ids)} chat IDs from Firebase")
            return chat_ids
            
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching chat IDs from Firebase: {str(e)}")
            return []
    
    def format_products_text(self, products: List[Dict[str, Any]]) -> str:
        """
        Format the scraped products into a single text message
        
        Args:
            products (List[Dict]): List of product dictionaries
            
        Returns:
            str: Formatted text string
        """
        if not products:
            return "🚫 No available products found at this time."
        
        header = f"🎮 Pokemon Store Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"📦 Found {len(products)} available products:\n\n"
        
        product_lines = []
        for idx, product in enumerate(products, 1):
            title = product.get('title', 'Unknown Product')
            price = product.get('price', 'Price not available')
            url = product.get('url', '')
            status = product.get('availability_status', 'Status unknown')
            
            product_line = f"{idx}. 🎯 {title}\n"
            product_line += f"   💰 {price}\n"
            if url:
                product_line += f"   🔗 {url}\n"
            product_line += f"   ✅ {status}\n"
            
            product_lines.append(product_line)
        
        footer = f"\n🤖 Automated scraping completed at {datetime.now().strftime('%H:%M:%S')}"
        
        return header + "\n".join(product_lines) + footer
    
    def send_to_telegram_chats(self, message: str, chat_ids: List[str]) -> Dict[str, bool]:
        """
        Send message to multiple Telegram chats
        
        Args:
            message (str): Message to send
            chat_ids (List[str]): List of chat IDs to send to
            
        Returns:
            Dict[str, bool]: Dictionary mapping chat_id to success status
        """
        if not self.telegram_initialized:
            print(f"[{datetime.now()}] Telegram not initialized. Cannot send messages.")
            return {}
        
        if not chat_ids:
            print(f"[{datetime.now()}] No chat IDs provided.")
            return {}
        
        results = {}
        
        for chat_id in chat_ids:
            try:
                # Split long messages if needed (Telegram has a 4096 character limit)
                if len(message) > 4000:
                    # Split message into chunks
                    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            self.telegram_bot.send_message(chat_id, chunk)
                        else:
                            self.telegram_bot.send_message(chat_id, f"...continued\n{chunk}")
                else:
                    self.telegram_bot.send_message(chat_id, message)
                
                results[chat_id] = True
                print(f"[{datetime.now()}] Successfully sent message to chat ID: {chat_id}")
                
            except Exception as e:
                results[chat_id] = False
                print(f"[{datetime.now()}] Failed to send message to chat ID {chat_id}: {str(e)}")
        
        return results
    
    def notify_products(self, products: List[Dict[str, Any]], chat_ids_path='/telegram_chat_ids') -> bool:
        """
        Complete notification workflow: fetch chat IDs, format message, and send
        
        Args:
            products (List[Dict]): List of scraped products
            chat_ids_path (str): Firebase path for chat IDs
            
        Returns:
            bool: True if at least one message was sent successfully
        """
        try:
            # Get chat IDs from Firebase
            chat_ids = self.get_chat_ids_from_firebase(chat_ids_path)
            
            if not chat_ids:
                print(f"[{datetime.now()}] No chat IDs available for notification.")
                return False
            
            # Format products into text message
            message = self.format_products_text(products)
            
            # Send to all chat IDs
            results = self.send_to_telegram_chats(message, chat_ids)
            
            # Check if at least one message was sent successfully
            success_count = sum(1 for success in results.values() if success)
            total_chats = len(results)
            
            print(f"[{datetime.now()}] Notification summary: {success_count}/{total_chats} messages sent successfully")
            
            return success_count > 0
            
        except Exception as e:
            print(f"[{datetime.now()}] Error in notification workflow: {str(e)}")
            return False


# Convenience function for easy integration
def create_notification_service():
    """Create a notification service with environment variables"""
    return NotificationService()