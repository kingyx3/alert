#!/usr/bin/env python3

"""
Configuration example for Telegram channel integration

To use the notification features:

1. Set up Telegram Bot:
   - Create a bot via @BotFather on Telegram
   - Get the bot token
   - Store the token in TELEGRAM_BOT_TOKEN environment variable or repo secret

2. Set up Telegram Channel:
   - Create a Telegram channel for store alerts
   - Add your bot as an administrator to the channel
   - Get the channel ID (it will be a negative number for channels, e.g. "-1001234567890")
   - Store the channel ID in TELEGRAM_CHANNEL_ID environment variable or repo secret

3. Environment variables to set:
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHANNEL_ID="-1001234567890"

4. For GitHub Actions (using repo secrets):
   - Go to your repository settings
   - Navigate to Secrets and variables > Actions
   - Add TELEGRAM_BOT_TOKEN as a secret
   - Add TELEGRAM_CHANNEL_ID as a secret

5. To get your Telegram channel ID:
   - Add your bot to the channel as admin
   - Send a message to the channel
   - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   - Look for the "chat" -> "id" value in the response (it will be negative for channels)
"""

import os

# Example environment setup (uncomment and modify as needed)
"""
os.environ['TELEGRAM_BOT_TOKEN'] = 'your_telegram_bot_token_here'
os.environ['TELEGRAM_CHANNEL_ID'] = '-1001234567890'  # Channel ID (negative number)
"""

# Example channel setup:
TELEGRAM_SETUP_EXAMPLE = {
    "bot_token": "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",  # From @BotFather
    "channel_id": "-1001234567890",  # Channel ID (always negative)
    "channel_username": "@store_alerts",  # Optional: Channel username
    "description": "Store availability notifications"
}