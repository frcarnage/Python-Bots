from telethon import TelegramClient, events
from telethon.tl.types import KeyboardButtonCallback, KeyboardButtonUrl
from telethon.sessions import StringSession
import asyncio
import re
import logging
from datetime import datetime
import json
import os
import sys

# ========== CONFIGURATION ==========
API_ID = 37560131  # Your API ID
API_HASH = '7f75273f77dcdf2fc355bc47142bb0a6'  # Your API Hash
SESSION_STRING = ""  # Leave empty for first run, then paste session string here

# Files for storage
SESSION_FILE = "session.txt"
GROUPS_FILE = "monitored_groups.json"
STATS_FILE = "rain_stats.json"

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== RAIN MONITOR CLASS ==========
class AutoRainJoiner:
    def __init__(self, client):
        self.client = client
        self.monitored_groups = {}
        self.detected_rains = []
        self.auto_join = True  # Auto join when button found
        self.stealth_mode = True  # No messages in groups
        self.last_notification = None
        
        # Rain detection patterns
        self.rain_patterns = [
            r'/rain\s+(\d+(?:\.\d+)?)\$?',
            r'rain\s+(\d+(?:\.\d+)?)\$?\s+',
            r'\$(\d+(?:\.\d+)?)\s+rain',
            r'(\d+(?:\.\d+)?)\s*\$\s*rain',
            r'(\d+(?:\.\d+)?)\s*usdt?\s+rain',
            r'(\d+(?:\.\d+)?)\s*usd\s+giveaway',
        ]
        
        self.rain_keywords = [
            '/rain', 'rain!', 'raining', 'giveaway', 'hosted by',
            'participants', 'received', 'each', 'free', 'crypto',
            'airdrop', 'distribution', 'reward', 'prize'
        ]
        
        self.join_keywords = ['join', 'participate', 'claim', 'tap', 'click', 'get']
        
        # Load data
        self.load_data()
    
    def load_data(self):
        """Load groups and stats from files"""
        # Load groups
        try:
            if os.path.exists(GROUPS_FILE):
                with open(GROUPS_FILE, 'r') as f:
                    data = json.load(f)
                    self.monitored_groups = data.get('groups', {})
        except:
            self.monitored_groups = {}
        
        # Load stats
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    data = json.load(f)
                    self.detected_rains = data.get('rains', [])
        except:
            self.detected_rains = []
    
    def save_data(self):
        """Save groups and stats to files"""
        # Save groups
        try:
            groups_data = {'groups': self.monitored_groups}
            with open(GROUPS_FILE, 'w') as f:
                json.dump(groups_data, f, indent=2)
        except:
            pass
        
        # Save stats (keep last 100)
        try:
            stats_data = {'rains': self.detected_rains[-100:]}
            with open(STATS_FILE, 'w') as f:
                json.dump(stats_data, f, indent=2)
        except:
            pass
    
    def extract_rain_info(self, text):
        """Extract rain amount and host from text"""
        amount = None
        host = "Unknown"
        
        # Extract amount
        for pattern in self.rain_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    break
                except:
                    continue
        
        # Extract host
        host_patterns = [
            r'hosted by\s+(@?\w+)',
            r'host:\s+(@?\w+)',
            r'by\s+(@?\w+)',
            r'from\s+(@?\w+)',
            r'host\s+(@?\w+)'
        ]
        
        for pattern in host_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                host = match.group(1).replace('@', '').strip()
                break
        
        # Fallback: find any @mention
        if host == "Unknown":
            mentions = re.findall(r'@(\w+)', text)
            if mentions:
                host = mentions[0]
        
        return amount, host
    
    def has_join_button(self, message):
        """Check if message has join button"""
        try:
            if not message.reply_markup:
                return False
            
            for row in message.reply_markup.rows:
                for button in row.buttons:
                    button_text = button.text.lower()
                    if any(keyword in button_text for keyword in self.join_keywords):
                        return True
        except:
            pass
        return False
    
    def get_join_button(self, message):
        """Get the join button if available"""
        try:
            if message.reply_markup:
                for row in message.reply_markup.rows:
                    for button in row.buttons:
                        button_text = button.text.lower()
                        if any(keyword in button_text for keyword in self.join_keywords):
                            return button
        except:
            pass
        return None
    
    async def send_saved_message(self, text):
        """Send message to saved messages"""
        try:
            await self.client.send_message('me', text)
        except Exception as e:
            logger.error(f"Error sending saved message: {e}")
    
    async def process_rain(self, event, chat_name):
        """Process a rain message"""
        try:
            message = event.message
            text = message.text or message.message
            
            if not text:
                return
            
            # Check if it's likely a rain message
            text_lower = text.lower()
            keyword_count = sum(1 for keyword in self.rain_keywords if keyword in text_lower)
            
            if keyword_count < 2 and '/rain' not in text_lower:
                return
            
            # Extract rain info
            amount, host = self.extract_rain_info(text)
            
            if amount is None:
                # Try to find any dollar amount
                dollar_match = re.search(r'\$(\d+(?:\.\d+)?)', text)
                if dollar_match:
                    amount = float(dollar_match.group(1))
            
            if amount is None:
                return  # Not a valid rain
            
            # Check for join button
            has_button = self.has_join_button(message)
            button = self.get_join_button(message) if has_button else None
            button_type = type(button).__name__ if button else "None"
            
            # Store rain info
            rain_info = {
                'id': f"{event.chat_id}_{message.id}",
                'chat_id': event.chat_id,
                'chat_name': chat_name,
                'message_id': message.id,
                'amount': amount,
                'host': host,
                'has_button': has_button,
                'button_type': button_type,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'auto_joined': False,
                'text_preview': text[:100]
            }
            
            # Add to history
            self.detected_rains.append(rain_info)
            
            # Send notification to saved messages
            timestamp = datetime.now().strftime("%H:%M:%S")
            notification = (
                f"🌧️ **Rain Detected!**\n\n"
                f"**Amount:** ${amount:.2f}\n"
                f"**Host:** @{host}\n"
                f"**Group:** {chat_name}\n"
                f"**Time:** {timestamp}\n"
                f"**Join Button:** {'✅ Available' if has_button else '❌ Not found'}\n"
            )
            
            if has_button:
                notification += f"**Auto-join:** {'🟢 ON' if self.auto_join else '🟡 OFF'}\n\n"
                
                if self.auto_join:
                    # Try to auto-join
                    joined = await self.auto_join_rain(event, button, rain_info)
                    notification += f"**Status:** {'✅ Joined' if joined else '❌ Failed'}"
                    rain_info['auto_joined'] = joined
                else:
                    notification += "**⚠️ Auto-join is OFF**\nSend `.join` to join manually"
            else:
                notification += "\n**ℹ️ No join button found**"
            
            await self.send_saved_message(notification)
            
            # Save data
            self.save_data()
            
            logger.info(f"Rain: ${amount} by @{host} | Button: {has_button}")
            
        except Exception as e:
            logger.error(f"Error processing rain: {e}")
            await self.send_saved_message(f"❌ Error processing rain: {str(e)}")
    
    async def auto_join_rain(self, event, button, rain_info):
        """Automatically join the rain"""
        try:
            message = event.message
            
            if isinstance(button, KeyboardButtonCallback):
                # Click the callback button
                await message.click(button=button)
                await asyncio.sleep(1)  # Wait for response
                return True
                
            elif isinstance(button, KeyboardButtonUrl):
                # For URL buttons, we can't click automatically
                await self.send_saved_message(
                    f"🔗 **URL Button Found**\n\n"
                    f"Rain: ${rain_info['amount']:.2f}\n"
                    f"Host: @{rain_info['host']}\n"
                    f"URL: {button.url}\n\n"
                    f"⚠️ Manual action required"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error auto-joining: {e}")
            await self.send_saved_message(f"❌ Auto-join failed: {str(e)}")
            return False
        
        return False
    
    async def manual_join_last(self):
        """Manually join the last detected rain"""
        try:
            if not self.detected_rains:
                await self.send_saved_message("❌ No recent rains found")
                return False
            
            last_rain = self.detected_rains[-1]
            
            if not last_rain['has_button']:
                await self.send_saved_message("❌ Last rain has no join button")
                return False
            
            # Get the message
            try:
                message = await self.client.get_messages(
                    last_rain['chat_id'],
                    ids=last_rain['message_id']
                )
                
                button = self.get_join_button(message)
                if not button:
                    await self.send_saved_message("❌ Could not find join button")
                    return False
                
                # Click the button
                await message.click(button=button)
                await asyncio.sleep(1)
                
                await self.send_saved_message(f"✅ Joined rain!\nAmount: ${last_rain['amount']:.2f}\nHost: @{last_rain['host']}")
                return True
                
            except Exception as e:
                await self.send_saved_message(f"❌ Error joining: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in manual join: {e}")
            return False

# ========== CLIENT SETUP ==========
async def get_client():
    """Create or load Telegram client"""
    # Check for saved session
    session_string = SESSION_STRING
    
    if not session_string and os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session_string = f.read().strip()
        except:
            pass
    
    if session_string:
        print("📱 Loading existing session...")
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    else:
        print("🔐 Creating new session...")
        client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    return client, session_string

async def save_session(client):
    """Save session string to file"""
    try:
        session_string = client.session.save()
        with open(SESSION_FILE, 'w') as f:
            f.write(session_string)
        print(f"💾 Session saved to {SESSION_FILE}")
        return session_string
    except Exception as e:
        print(f"❌ Error saving session: {e}")
        return None

# ========== COMMAND HANDLERS ==========
@client.on(events.NewMessage(pattern=r'^\.cmds$', outgoing=True))
async def cmds_handler(event):
    """Show all commands"""
    cmds_text = (
        "🤖 **Rain Auto-Joiner Commands**\n\n"
        "**🎯 Monitoring:**\n"
        "`.add` - Add current chat to monitoring\n"
        "`.remove` - Remove current chat\n"
        "`.list` - List monitored chats\n\n"
        "**⚙️ Settings:**\n"
        "`.auto on/off` - Toggle auto-join\n"
        "`.stealth on/off` - Toggle stealth mode\n\n"
        "**🔄 Actions:**\n"
        "`.join` - Manually join last rain\n"
        "`.stats` - Show statistics\n"
        "`.session` - Get session string\n"
        "`.cmds` - Show this help\n\n"
        "**ℹ️ Info:**\n"
        f"Monitored: {len(joiner.monitored_groups)} chats\n"
        f"Auto-join: {'ON ✅' if joiner.auto_join else 'OFF ❌'}\n"
        f"Stealth: {'ON ✅' if joiner.stealth_mode else 'OFF ❌'}"
    )
    
    await event.edit(cmds_text)
    await asyncio.sleep(5)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage(pattern=r'^\.add$', outgoing=True))
async def add_handler(event):
    """Add current chat to monitoring"""
    try:
        chat = await event.get_chat()
        chat_id = chat.id
        chat_name = getattr(chat, 'title', f"Chat_{chat_id}")
        
        joiner.monitored_groups[chat_id] = chat_name
        joiner.save_data()
        
        response = f"✅ **Added to monitoring:**\n{chat_name}\nID: `{chat_id}`"
        
        # Also send to saved messages
        await client.send_message('me', 
            f"✅ Chat added to monitoring:\n"
            f"**Name:** {chat_name}\n"
            f"**ID:** {chat_id}\n\n"
            f"Total monitored: {len(joiner.monitored_groups)}"
        )
        
        await event.edit(response)
        await asyncio.sleep(3)
        if event.is_group and joiner.stealth_mode:
            await event.delete()
            
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern=r'^\.remove$', outgoing=True))
async def remove_handler(event):
    """Remove current chat from monitoring"""
    try:
        chat_id = event.chat_id
        
        if chat_id in joiner.monitored_groups:
            removed_name = joiner.monitored_groups.pop(chat_id)
            joiner.save_data()
            
            response = f"✅ **Removed from monitoring:**\n{removed_name}"
            await client.send_message('me', 
                f"✅ Chat removed:\n**{removed_name}**\n"
                f"Remaining: {len(joiner.monitored_groups)}"
            )
        else:
            response = "❌ This chat is not being monitored"
        
        await event.edit(response)
        await asyncio.sleep(3)
        if event.is_group and joiner.stealth_mode:
            await event.delete()
            
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern=r'^\.list$', outgoing=True))
async def list_handler(event):
    """List monitored chats"""
    if not joiner.monitored_groups:
        await event.edit("❌ No chats being monitored")
        return
    
    list_text = "📋 **Monitored Chats:**\n\n"
    for chat_id, name in joiner.monitored_groups.items():
        list_text += f"• {name}\n   `ID: {chat_id}`\n"
    
    list_text += f"\n**Total:** {len(joiner.monitored_groups)} chats"
    
    await event.edit(list_text)
    await asyncio.sleep(5)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage(pattern=r'^\.stats$', outgoing=True))
async def stats_handler(event):
    """Show statistics"""
    total_rains = len(joiner.detected_rains)
    
    if total_rains == 0:
        stats_text = "📊 **Statistics**\n\nNo rains detected yet."
    else:
        total_amount = sum(r['amount'] for r in joiner.detected_rains if r.get('amount'))
        rains_with_buttons = sum(1 for r in joiner.detected_rains if r.get('has_button'))
        auto_joined = sum(1 for r in joiner.detected_rains if r.get('auto_joined'))
        
        # Last 24 hours
        day_ago = datetime.now().timestamp() - 86400
        recent_rains = [
            r for r in joiner.detected_rains 
            if datetime.strptime(r['timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() > day_ago
        ]
        
        stats_text = (
            f"📊 **Rain Statistics**\n\n"
            f"**Total Rains:** {total_rains}\n"
            f"**Total Amount:** ${total_amount:.2f}\n"
            f"**With Buttons:** {rains_with_buttons}\n"
            f"**Auto-Joined:** {auto_joined}\n"
            f"**Recent (24h):** {len(recent_rains)}\n\n"
            f"**Monitored Chats:** {len(joiner.monitored_groups)}\n"
            f"**Auto-Join:** {'✅ ON' if joiner.auto_join else '❌ OFF'}\n"
            f"**Stealth Mode:** {'✅ ON' if joiner.stealth_mode else '❌ OFF'}"
        )
        
        # Last rain info
        if joiner.detected_rains:
            last = joiner.detected_rains[-1]
            time_diff = datetime.now() - datetime.strptime(last['timestamp'], "%Y-%m-%d %H:%M:%S")
            minutes = int(time_diff.total_seconds() / 60)
            
            stats_text += f"\n\n**Last Rain:**\n${last['amount']:.2f} by @{last['host']}\n{minutes} minutes ago"
    
    await event.edit(stats_text)
    await asyncio.sleep(5)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage(pattern=r'^\.session$', outgoing=True))
async def session_handler(event):
    """Get session string"""
    try:
        session_string = await save_session(client)
        if session_string:
            await event.edit("✅ Session string saved to file")
            await client.send_message('me', 
                f"🔐 **Your Session String:**\n\n"
                f"`{session_string}`\n\n"
                f"⚠️ Keep this safe! Don't share with anyone."
            )
        else:
            await event.edit("❌ Could not save session")
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern=r'^\.auto (on|off)$', outgoing=True))
async def auto_handler(event):
    """Toggle auto-join"""
    mode = event.pattern_match.group(1)
    joiner.auto_join = (mode == 'on')
    
    status = "✅ ON" if joiner.auto_join else "❌ OFF"
    await event.edit(f"🤖 Auto-join: {status}")
    
    # Also notify in saved messages
    await client.send_message('me', 
        f"⚙️ **Settings Updated**\n\n"
        f"Auto-join: {status}\n"
        f"Next rain will {'automatically join' if joiner.auto_join else 'require manual join'}"
    )
    
    await asyncio.sleep(3)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage(pattern=r'^\.stealth (on|off)$', outgoing=True))
async def stealth_handler(event):
    """Toggle stealth mode"""
    mode = event.pattern_match.group(1)
    joiner.stealth_mode = (mode == 'on')
    
    status = "✅ ON" if joiner.stealth_mode else "❌ OFF"
    await event.edit(f"🕵️ Stealth mode: {status}")
    
    await client.send_message('me', 
        f"⚙️ **Stealth Mode**\n\n"
        f"Status: {status}\n"
        f"Bot responses: {'will auto-delete' if joiner.stealth_mode else 'will remain'}"
    )
    
    await asyncio.sleep(3)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage(pattern=r'^\.join$', outgoing=True))
async def join_handler(event):
    """Manually join last rain"""
    await event.edit("🔄 Attempting to join last rain...")
    
    success = await joiner.manual_join_last()
    
    if success:
        await event.edit("✅ Successfully joined last rain!")
    else:
        await event.edit("❌ Failed to join last rain")
    
    await asyncio.sleep(3)
    if event.is_group and joiner.stealth_mode:
        await event.delete()

@client.on(events.NewMessage())
async def message_monitor(event):
    """Monitor all messages for rains"""
    # Skip our own messages
    if event.out:
        return
    
    # Skip if not in monitored group
    if event.chat_id not in joiner.monitored_groups:
        return
    
    # Get chat name
    chat_name = joiner.monitored_groups.get(event.chat_id, f"Chat_{event.chat_id}")
    
    # Process message for rain
    await joiner.process_rain(event, chat_name)

# ========== MAIN FUNCTION ==========
async def main():
    global client, joiner
    
    # Get client
    client, existing_session = await get_client()
    
    print("\n" + "="*50)
    print("🤖 RAIN AUTO-JOINER BOT")
    print("="*50)
    print(f"📱 API ID: {API_ID}")
    print(f"🔑 Session: {'Loaded ✅' if existing_session else 'New 🔄'}")
    print("="*50)
    
    await client.start()
    
    # Save session if new
    if not existing_session:
        session_string = await save_session(client)
        print(f"💾 New session created and saved")
        
        # Send session to saved messages
        if session_string:
            await client.send_message('me', 
                f"🔐 **New Session Created**\n\n"
                f"Your session string:\n\n"
                f"`{session_string}`\n\n"
                f"⚠️ Save this string!\n"
                f"Use it next time to avoid login."
            )
    
    # Initialize joiner
    joiner = AutoRainJoiner(client)
    
    print(f"📊 Monitored chats: {len(joiner.monitored_groups)}")
    print(f"🌧️ Previous rains: {len(joiner.detected_rains)}")
    print(f"🤖 Auto-join: {'ON ✅' if joiner.auto_join else 'OFF ❌'}")
    print(f"🕵️ Stealth: {'ON ✅' if joiner.stealth_mode else 'OFF ❌'}")
    print("="*50)
    print("\n📝 **Available Commands:**")
    print("• .cmds - Show all commands")
    print("• .add - Add current chat")
    print("• .stats - Show statistics")
    print("• .session - Get session string")
    print("\n🔔 Notifications → Saved Messages")
    print("🎯 Auto-join → When button found")
    print("="*50 + "\n")
    
    # Send startup message
    await client.send_message('me',
        f"🤖 **Rain Auto-Joiner Started!**\n\n"
        f"✅ Status: Online\n"
        f"📊 Monitored: {len(joiner.monitored_groups)} chats\n"
        f"🌧️ Previous: {len(joiner.detected_rains)} rains\n"
        f"🤖 Auto-join: {'✅ ON' if joiner.auto_join else '❌ OFF'}\n"
        f"🕵️ Stealth: {'✅ ON' if joiner.stealth_mode else '❌ OFF'}\n\n"
        f"**Commands:**\n"
        f"• `.cmds` - Show all commands\n"
        f"• `.add` - Add current chat\n"
        f"• `.stats` - Show statistics\n\n"
        f"🔔 You'll get notifications here when rains are detected!"
    )
    
    print("✅ Bot is running...")
    print("💡 Send `.add` in any group to start monitoring")
    print("💡 Send `.cmds` to see all commands")
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    print("🤖 Bot starting on Replit...")
    
    # Keep-alive for Replit
    async def keep_alive():
        while True:
            await asyncio.sleep(300)  # Ping every 5 minutes
            print("🔄 Still running...")
    
    # Run both tasks
    async def main():
        task1 = asyncio.create_task(client.run_until_disconnected())
        task2 = asyncio.create_task(keep_alive())
        await asyncio.gather(task1, task2)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
    except Exception as e:
        print(f"Error: {e}")
        # Auto-restart
        os.execv(sys.executable, ['python'] + sys.argv)
