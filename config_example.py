#!/usr/bin/env python3

"""
Configuration example for Firebase and Telegram integration

To use the notification features:

1. Set up Firebase Realtime Database:
   - Create a Firebase project at https://console.firebase.google.com/
   - Enable Realtime Database
   - Generate a service account key (JSON file)
   - Store the service account file path in FIREBASE_SERVICE_ACCOUNT_PATH env var
   - Set your database URL in FIREBASE_DATABASE_URL env var

2. Set up Telegram Bot:
   - Create a bot via @BotFather on Telegram
   - Get the bot token
   - Store the token in TELEGRAM_BOT_TOKEN env var

3. Configure chat IDs in Firebase:
   - In your Firebase Realtime Database, create a structure like:
   
   {
     "telegram_chat_ids": [
       "123456789",
       "987654321",
       "555666777"
     ]
   }
   
   OR as an object:
   
   {
     "telegram_chat_ids": {
       "user1": "123456789",
       "user2": "987654321", 
       "group1": "555666777"
     }
   }

4. Environment variables to set:
   export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/serviceAccount.json"
   export FIREBASE_DATABASE_URL="https://your-project-id-default-rtdb.firebaseio.com/"
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"

5. To get your Telegram chat ID:
   - Message your bot
   - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   - Look for the "chat" -> "id" value in the response
"""

import os

# Example environment setup (uncomment and modify as needed)
"""
os.environ['FIREBASE_SERVICE_ACCOUNT_PATH'] = '/path/to/your/serviceAccount.json'
os.environ['FIREBASE_DATABASE_URL'] = 'https://your-project-id-default-rtdb.firebaseio.com/'
os.environ['TELEGRAM_BOT_TOKEN'] = 'your_telegram_bot_token_here'
"""

# Firebase Realtime Database structure example:
FIREBASE_STRUCTURE_EXAMPLE = {
    "telegram_chat_ids": [
        "123456789",  # User 1 chat ID
        "987654321",  # User 2 chat ID  
        "-555666777"  # Group chat ID (groups have negative IDs)
    ],
    "settings": {
        "notification_enabled": True,
        "scrape_interval_minutes": 60
    }
}

# Alternative Firebase structure as object:
FIREBASE_STRUCTURE_ALTERNATIVE = {
    "telegram_chat_ids": {
        "user_alice": "123456789",
        "user_bob": "987654321",
        "pokemon_group": "-555666777"
    }
}