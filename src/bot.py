# Standard library imports
import logging
from datetime import datetime, timezone, timedelta, time

# Third-party imports
from telegram.error import NetworkError, TelegramError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Local imports
from config.config import Config
from config.timezones_config import REGION_TIMEZONES
from database.db_handler import DatabaseHandler
from models_dir.models import Link, Reminder, User, UserAnalytics
from utils.url_extractor import extract_urls
from utils.logging_config import setup_logging
from utils.rate_limiter import RateLimiter

config = Config.get_instance()
rate_limiter = RateLimiter()
# Set up logging - this is now our only logging configuration
setup_logging()
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((NetworkError, TimedOut))
)
async def send_message_with_retry(update, text, reply_markup=None):
    """Send message with retry logic"""
    try:
        return await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise

async def start(update, context):
    user_id = update.message.from_user.id
    db = DatabaseHandler()
    session = None
    try:
        session = db.get_session()
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id)
            session.add(user)
            session.commit()

        if not user.timezone:
            await update.message.reply_text(
                f"Hi {update.effective_user.first_name}! 👋\n"
                "I can help you save links and send reminders.\n\n"
                "To ensure reminders are sent at the correct time, please set your time zone using /set_timezone. "
            )
        else:
            await update.message.reply_text(
                f"Hi {update.effective_user.first_name}! 👋\n"
                "You're all set! Send me a link to save it for later."
            )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

async def help_command(update, context):
    """Send a message when the command /help is issued."""
    help_text = """
    Here's what I can do:
    - Send me any link to save it
    - Use /list to see your saved links
    - Use /help to see this message
    """
    await update.message.reply_text(help_text)

async def set_timezone(update, context):
    """Handles the initial region selection step."""
    regions = list(REGION_TIMEZONES.keys())  # Extract regions from the config
    keyboard = [[InlineKeyboardButton(region, callback_data=f"region_{region}")] for region in regions]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please select your region:", reply_markup=reply_markup
    )

async def handle_region_selection(update, context):
    """Handles the region selection and shows available timezones for that region."""
    query = update.callback_query
    await query.answer()

    # Extract selected region
    selected_region = query.data.replace("region_", "")
    
    # Get timezones for the selected region
    if selected_region not in REGION_TIMEZONES:
        await query.edit_message_text("Invalid region selected. Please try again using /set_timezone")
        return

    timezones = REGION_TIMEZONES[selected_region]
    
    # Create keyboard with timezone options
    keyboard = []
    for timezone_name, offset in timezones:
        # Convert offset to string with sign
        offset_str = f"+{offset}" if offset >= 0 else str(offset)
        callback_data = f"timezone_{offset}"
        keyboard.append([InlineKeyboardButton(timezone_name, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Selected region: {selected_region}\nPlease choose your timezone:",
        reply_markup=reply_markup
    )

async def handle_timezone_selection(update, context):
    """Handles the timezone selection and saves it to the database."""
    query = update.callback_query
    await query.answer()

    try:
        # Extract the selected timezone offset
        selected_offset = float(query.data.replace("timezone_", ""))
        user_id = query.from_user.id

        # Save timezone to database
        db = DatabaseHandler()
        session = db.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                user.timezone = str(selected_offset)  # Store as string for consistency
                user.has_set_timezone = True
                session.commit()
                
                # Format offset for display
                offset_str = f"+{selected_offset}" if selected_offset >= 0 else str(selected_offset)
                await query.edit_message_text(
                    f"✅ Your timezone has been set to UTC{offset_str}.\n\n"
                    "You can now send me links to save them!"
                )
            else:
                await query.edit_message_text(
                    "⚠️ Error: User not found. Please try again using /set_timezone"
                )
        finally:
            session.close()
            
    except (ValueError, Exception) as e:
        logger.error(f"Error in timezone selection: {str(e)}")
        await query.edit_message_text(
            "⚠️ Error setting timezone. Please try again using /set_timezone"
        )

def get_user_local_time(utc_time, user_timezone_offset):
    """Convert UTC time to user's local time"""
    try:
        offset = float(user_timezone_offset)
        return utc_time + timedelta(hours=offset)
    except (ValueError, TypeError):
        return utc_time

def get_utc_time(local_time, user_timezone_offset):
    """Convert user's local time to UTC"""
    try:
        offset = float(user_timezone_offset)
        return local_time - timedelta(hours=offset)
    except (ValueError, TypeError):
        return local_time

# In bot.py

# Update the import
from utils.url_extractor import extract_urls

async def handle_message(update, context):
    """Handle incoming messages with rate limiting"""
    message_text = update.message.text
    user_id = update.message.from_user.id

    # Check message rate limit
    is_allowed, error_msg = rate_limiter.check_rate_limit(user_id, 'messages')
    if not is_allowed:
        await update.message.reply_text(error_msg)
        return

    # Extract and validate URLs
    valid_urls, error_messages = extract_urls(message_text)

    if valid_urls:
        # Check link rate limit
        is_allowed, error_msg = rate_limiter.check_rate_limit(user_id, 'links')
        if not is_allowed:
            await update.message.reply_text(error_msg)
            return

        # Process valid URLs
        try:
            saved_count = await save_link_logic(update, context, valid_urls)
            logger.info(f"Saved {saved_count} links for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save links: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error while saving your links. Please try again later."
            )

    # Handle validation errors
    if error_messages:
        error_text = "\n".join(f"❌ {error}" for error in error_messages)
        if valid_urls:
            await update.message.reply_text(
                "Some URLs couldn't be saved:\n" + error_text
            )
        else:
            await update.message.reply_text(
                "Unable to save URLs:\n" + error_text
            )
    elif not valid_urls:
        await update.message.reply_text(
            "Please send me a link to save it for later! 🔍\n"
            "The link should start with http:// or https://"
        )
        
# Placeholder function to simulate logging user actions
def log_invalid_input(user_id, message_text):
    """Simulates logging an invalid input action for now."""
    # This is a mock log entry to show what would be logged
    mock_log_entry = {
        "user_id": user_id,
        "action_type": "invalid_input",
        "action_data": {"message_text": message_text},
        "created_at": datetime.now(timezone.utc)  # Use timezone-aware UTC datetime
    }
    print("Logged action:", mock_log_entry)

async def save_link_logic(update, context, urls):
    """Enhanced save_link_logic with better error handling"""
    db = DatabaseHandler()
    session = None
    try:
        session = db.get_session()
        
        user_id = update.message.from_user.id
        username = update.message.from_user.username
        first_name = update.message.from_user.first_name
        
        logger.info(f"Attempting to save links for user {user_id}")
        
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            logger.info(f"Creating new user with telegram_id {user_id}")
            user = User(
                telegram_id=user_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            session.commit()

        saved_count = 0
        for url in urls:
            try:
                link = Link(
                    user_id=user.id,
                    url=url
                )
                session.add(link)
                session.flush()  # Get the link ID without committing

                user_timezone = user.timezone if user else None
                now = datetime.now(timezone.utc)
                local_reminder_time = get_user_local_time(now, user_timezone).replace(
                    hour=9, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                utc_reminder_time = get_utc_time(local_reminder_time, user_timezone)
                
                reminder = Reminder(
                    link_id=link.id,
                    remind_at=utc_reminder_time,
                    is_default_time=True
                )
                session.add(reminder)
                session.flush()

                # Update analytics
                db.update_user_analytics(user.id, 'link_saved', session=session)
                db.update_user_analytics(user.id, 'default_passive', session=session)

                saved_count += 1
                
                # Create reminder setting keyboard
                keyboard = [
                    [
                        InlineKeyboardButton("Tomorrow", callback_data=f"tomorrow_{reminder.id}"),
                        InlineKeyboardButton("In 2 Days", callback_data=f"2days_{reminder.id}")
                    ],
                    [
                        InlineKeyboardButton("In 3 Days", callback_data=f"3days_{reminder.id}"),
                        InlineKeyboardButton("Skip", callback_data=f"skip_{reminder.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"Link saved: {url}",
                    reply_markup=reply_markup
                )

            except Exception as e:
                logger.error(f"Error saving specific link {url}: {str(e)}")
                await update.message.reply_text(f"Failed to save link: {url}")
                continue

        session.commit()
        return saved_count

    except Exception as e:
        logger.error(f"Error in save_link_logic: {str(e)}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()


async def handle_reminder_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    session = None
    
    try:
        # Get callback data
        callback_data = query.data
        
        # Skip if this is a timezone-related callback
        if callback_data.startswith(('region_', 'timezone_')):
            return
            
        # Parse the command and reminder_id
        command, reminder_id = callback_data.split("_")
        reminder_id = int(reminder_id)

        db = DatabaseHandler()
        session = db.get_session()

        # Get the reminder
        reminder = session.query(Reminder).filter_by(id=reminder_id).first()
        if not reminder:
            logger.warning(f"Reminder {reminder_id} not found")
            return

        # Get user's timezone
        user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
        user_timezone = user.timezone if user else None
        
        # Use UTC time as base
        now = datetime.now(timezone.utc)

        if command == "skip":
            db.update_user_analytics(user.id, 'active_skip', session=session)
            # Convert to user's local time, set to 9 AM, then convert back to UTC
            local_time = get_user_local_time(now, user_timezone)
            local_next_day = local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            utc_next_day = get_utc_time(local_next_day, user_timezone)
            
            reminder.remind_at = utc_next_day
            reminder.is_default_time = True
            session.commit()
            # Just remove the keyboard
            await query.edit_message_reply_markup(None)
            db.update_user_analytics(user.id, 'default_reminder', session=session)
            
        else:
            # Calculate days based on command
            days_map = {
                "tomorrow": 1,
                "2days": 2,
                "3days": 3
            }
            
            if command in days_map:
                days = days_map[command]
                # Convert to user's local time, set to 9 AM, then convert back to UTC
                local_time = get_user_local_time(now, user_timezone)
                local_remind_time = local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days)
                utc_remind_time = get_utc_time(local_remind_time, user_timezone)
                
                reminder.remind_at = utc_remind_time
                reminder.is_default_time = False
                session.commit()
                
                # Send confirmation using user's local time
                db.update_user_analytics(user.id, 'manual_reminder', session=session)
                db.update_user_analytics(user.id, 'default_reminder_removed', session=session)  # Decrement default count
                formatted_date = get_user_local_time(utc_remind_time, user_timezone).strftime("%B %d at 9:00 AM")
                await query.edit_message_text(f"✅ Reminder set for {formatted_date}")

    except Exception as e:
        logger.error(f"Error in reminder callback: {str(e)}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

async def send_due_reminders(bot, db_handler):
    """Find and send due reminders."""
    session = None
    try:
        session = db_handler.get_session()
        current_utc = datetime.now(timezone.utc)
        
        due_reminders = (
            session.query(Reminder)
            .join(Link)
            .join(User)
            .filter(
                Reminder.status == 'pending',
                Reminder.remind_at <= current_utc
            )
            .all()
        )
        
        if due_reminders:
            logger.info(f"Found {len(due_reminders)} due reminders")
            
            for reminder in due_reminders:
                try:
                    keyboard = [[InlineKeyboardButton(
                        "Remind me tomorrow", 
                        callback_data=f"snooze_{reminder.id}"
                    )]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await bot.send_message(
                        chat_id=reminder.link.user.telegram_id,
                        text=f"🔔 Time to read: {reminder.link.url}",
                        reply_markup=reply_markup
                    )
                    
                    reminder.status = 'sent'
                    reminder.last_reminded_at = current_utc
                    logger.info(f"Sent reminder {reminder.id} to user {reminder.link.user.telegram_id}")
                    reminder.status = 'sent'
                    db.update_user_analytics(reminder.link.user.id, 'reminder_completed', session=session)
                    
                except Exception as e:
                    logger.error(f"Failed to send reminder {reminder.id}: {str(e)}")
                    continue
            
            session.commit()
        
    except Exception as e:
        logger.error(f"Error processing reminders: {str(e)}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

async def check_reminders_job(context: CallbackContext):
    """
    Job function to check and send due reminders.
    This function runs every 5 minutes via the job queue.
    """
    logger.info("Running scheduled reminder check...")
    try:
        db = DatabaseHandler()
        await send_due_reminders(context.bot, db)
    except Exception as e:
        logger.error(f"Error in reminder check job: {str(e)}")

# Manual Test for reminders
async def check_reminders_command(update: Update, context: CallbackContext):
    """Manual command to check reminders for testing."""
    await update.message.reply_text("Checking reminders...")
    db = DatabaseHandler()
    await send_due_reminders(context.bot, db)
    await update.message.reply_text("Reminder check completed!")

async def check_missed_reminders(bot, db_handler):
    """Check for reminders that weren't interacted with in 24 hours"""
    session = None
    try:
        session = db_handler.get_session()
        current_utc = datetime.now(timezone.utc)
        cutoff_time = current_utc - timedelta(hours=24)
        
        missed_reminders = (
            session.query(Reminder)
            .join(Link)
            .join(User)
            .filter(
                Reminder.status == 'sent',
                Reminder.last_reminded_at <= cutoff_time,
                Reminder.is_snoozed == False
            )
            .all()
        )
        
        for reminder in missed_reminders:
            try:
                reminder.status = 'missed'
                db_handler.update_user_analytics(
                    reminder.link.user.id, 
                    'reminder_missed', 
                    session=session
                )
            except Exception as e:
                logger.error(f"Failed to process missed reminder {reminder.id}: {str(e)}")
                continue
                
        session.commit()
        
    except Exception as e:
        logger.error(f"Error checking missed reminders: {str(e)}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

async def check_missed_reminders_job(context: CallbackContext):
    """Job function to check missed reminders daily"""
    logger.info("Running missed reminders check...")
    try:
        db = DatabaseHandler()
        await check_missed_reminders(context.bot, db)
    except Exception as e:
        logger.error(f"Error in missed reminders check job: {str(e)}")

async def handle_snooze(update: Update, context: CallbackContext):
    """Handle snooze button clicks."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Get reminder ID from callback data
        reminder_id = int(query.data.replace("snooze_", ""))
        
        # Get reminder from database
        db = DatabaseHandler()
        session = db.get_session()
        
        try:
            reminder = session.query(Reminder).get(reminder_id)
            
            if reminder:
                # Get user's timezone
                user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
                user_timezone = user.timezone if user else None
                
                # Set new reminder time for tomorrow at 9 AM in user's timezone
                now = datetime.now(timezone.utc)
                local_time = get_user_local_time(now, user_timezone)
                local_next_day = local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                utc_next_day = get_utc_time(local_next_day, user_timezone)
                
                reminder.remind_at = utc_next_day
                reminder.status = 'pending'
                reminder.is_snoozed = True
                reminder.snooze_count += 1
                session.commit()
                reminder.remind_at = utc_next_day
                db.update_user_analytics(user.id, 'snooze', session=session)
                local_time = get_user_local_time(utc_next_day, user_timezone)
                formatted_time = local_time.strftime("%B %d at %I:%M %p")
                await query.edit_message_text(
                    f"Reminder snoozed until {formatted_time}",
                    reply_markup=None
                )
            else:
                await query.edit_message_text(
                    "⚠️ Error: Reminder not found.",
                    reply_markup=None
                )
                
        except Exception as e:
            logger.error(f"Error in snooze handler: {str(e)}")
            await query.edit_message_text(
                "⚠️ Failed to snooze reminder. Please try again later.",
                reply_markup=None
            )
            if session:
                session.rollback()
        finally:
            if session:
                session.close()
                
    except Exception as e:
        logger.error(f"Error parsing snooze callback: {str(e)}")
        await query.edit_message_text(
            "⚠️ An error occurred. Please try again later.",
            reply_markup=None
        )

# This function will log any exceptions that occur while the bot processes updates.
async def error_handler(update, context):
    """Log errors and notify the user if possible."""
    try:
        raise context.error
    except NetworkError as e:
        error_msg = f"Network error occurred: {e}" if config.DEBUG else "A network error occurred"
        logger.error(error_msg)
        if update and update.message:
            await update.message.reply_text(
                error_msg if config.DEBUG else "Sorry, network issues. Please try again later."
            )
    except TelegramError as e:
        error_msg = f"Telegram error occurred: {e}" if config.DEBUG else "A Telegram error occurred"
        logger.error(error_msg)
        if update and update.message:
            await update.message.reply_text(
                error_msg if config.DEBUG else "Sorry, there was an error with Telegram. Please try again."
            )
    except Exception as e:
        # Log the full error details
        error_msg = f"An unexpected error occurred: {str(e)}"
        if config.DEBUG:
            import traceback
            error_msg += f"\n\nTraceback:\n{''.join(traceback.format_tb(e.__traceback__))}"
        logger.error(error_msg)
        
        # Send appropriate message to user
        if update and update.message:
            if config.DEBUG:
                await update.message.reply_text(
                    f"Debug Error Info:\n{str(e)}\n\n"
                    "This detailed error is shown because DEBUG=True"
                )
            else:
                await update.message.reply_text(
                    "Sorry, an unexpected error occurred. Please try again later."
                )

def main():
    """Start the bot."""
    try:
        print("Attempting to start bot...")
        
        # Create the Application
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("set_timezone", set_timezone))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add timezone handlers BEFORE the general reminder handler
        application.add_handler(CallbackQueryHandler(handle_region_selection, pattern="^region_"))
        application.add_handler(CallbackQueryHandler(handle_timezone_selection, pattern="^timezone_"))
        
        # Add snooze handler
        application.add_handler(CallbackQueryHandler(handle_snooze, pattern="^snooze_"))

        # Add reminder handler last (as it's more generic)
        application.add_handler(CallbackQueryHandler(handle_reminder_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)

        # Set up job queue for checking reminders
        job_queue = application.job_queue
        job_queue.run_repeating(check_reminders_job, interval=300, first=10)  # 300 seconds = 5 minutes
        logger.info("Reminder check job scheduled to run every 5 minutes")
        job_queue.run_daily(check_missed_reminders_job, time=time(hour=0, minute=0))

        # Start the Bot
        print("Bot is starting...")
        application.run_polling()
        print("Polling started")

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"Error: {e}")

if __name__ == '__main__':
    main()

