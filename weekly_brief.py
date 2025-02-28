# weekly_brief.py
import logging
import csv
import asyncio
import sys
from datetime import datetime, timedelta
from telegram import Bot
from config.config import Config

# Detailed CSV loading with comma-separated handling
# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   filename='logs/weekly_brief.log')
logger = logging.getLogger(__name__)

# Detailed CSV loading with comma-separated handling
def load_brief_data(file_path):
    """Load user links and summaries from CSV file"""
    briefs = {}
    try:
        print(f"Attempting to read file: {file_path}")
        
        # Open the file and read with CSV reader
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Use csv reader with comma delimiter and quote handling
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            
            for row_num, row in enumerate(reader, start=1):
                print(f"Processing row {row_num}: {row}")
                
                # Skip empty rows
                if not row or all(cell.strip() == '' for cell in row):
                    print(f"Skipping empty row {row_num}")
                    continue
                
                # Ensure we have at least 3 columns
                if len(row) < 3:
                    print(f"Skipping row {row_num} - not enough columns")
                    continue
                
                try:
                    # Parse Telegram ID
                    user_id = int(float(row[0].strip()))
                    
                    # Parse URL
                    url = row[1].strip()
                    
                    # Parse summary (might be multi-line)
                    summary = row[2].strip()
                    
                    # Process summary to clean up and format
                    summary_lines = summary.replace('\t', '').split('\n')
                    # Remove empty lines and clean up bullet points
                    summary_lines = [
                        line.replace('-', '•').strip() 
                        for line in summary_lines 
                        if line.strip()
                    ]
                    
                    # Reconstruct summary
                    formatted_summary = '\n'.join(summary_lines)
                    
                    # Add to briefs
                    if user_id not in briefs:
                        briefs[user_id] = []
                    
                    briefs[user_id].append({
                        'url': url,
                        'summary': formatted_summary
                    })
                    
                    print(f"Added brief for user {user_id}")
                    
                except (ValueError, TypeError, IndexError) as e:
                    print(f"Error processing row {row_num}: {e}")
                    print(f"Problematic row: {row}")
                    logger.error(f"Error processing row {row_num}: {e}")
                    continue
            
            print(f"Loaded briefs for {len(briefs)} users")
            logger.info(f"Loaded briefs for {len(briefs)} users")
        return briefs
    
    except Exception as e:
        print(f"CRITICAL ERROR loading CSV: {e}")
        logger.critical(f"CRITICAL ERROR loading CSV: {e}")
        # If possible, print more details about the error
        import traceback
        traceback.print_exc()
        return {}

# Format the brief for each user
def format_brief(links_data, user_id):
    """Format a weekly brief from a list of link data"""
    # Get the current date for the brief
    today = datetime.now()
    
    # Calculate the start and end of the week
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Format the date range
    week_start_str = start_of_week.strftime("%B %d")
    week_end_str = end_of_week.strftime("%d, %Y")
    
    # Intro text for the brief
    brief = f"📋 Your Weekly Reading Digest\n\n"
    brief += f"Here's a summary of links you saved this week:\n\n"
    
    # Add each link and its summary
    for i, link in enumerate(links_data, 1):
        # Add the summary, preserving formatting
        summary = link['summary'].strip()
        
        # Add the summary to the brief, with a numbered header if multiple links
        if len(links_data) > 1:
            brief += f"{i}. {summary}\n\n"
        else:
            brief += f"{summary}\n\n"
    
    # Add a link to the original URL if possible
    if links_data:
        brief += "Original links:\n"
        for link in links_data:
            brief += f"🔗 {link['url']}\n"
    
    # Closing message
    brief += "\nHave a great weekend of reading! 📚\n"
    
    return brief

# Send the brief 
async def send_brief(bot, user_id, brief_text):
    """Send weekly brief"""
    try:
        print(f"Attempting to send brief to user {user_id}")
        await bot.send_message(
            chat_id=user_id,
            text=brief_text,
            disable_web_page_preview=True
        )
        print(f"Successfully sent brief to user {user_id}")
        logger.info(f"Sent brief to user {user_id}")
        return True
    except Exception as e:
        print(f"Error sending brief to user {user_id}: {e}")
        logger.error(f"Error sending brief to user {user_id}: {e}")
        return False

# Main function to send all briefs
async def send_weekly_briefs(file_path):
    """Send weekly briefs to all users in the CSV file"""
    try:
        config = Config.get_instance()
        bot = Bot(token=config.TELEGRAM_TOKEN)
        
        # Load data
        briefs_data = load_brief_data(file_path)
        if not briefs_data:
            print("No brief data loaded, exiting.")
            logger.error("No brief data loaded, exiting.")
            return
        
        # Send briefs
        success_count = 0
        failure_count = 0
        
        for user_id, links in briefs_data.items():
            try:
                # Format the brief
                brief_text = format_brief(links, user_id)
                print(f"Brief for user {user_id}:\n{brief_text}")
                
                # Send the brief
                success = await send_brief(bot, user_id, brief_text)
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                print(f"Unexpected error sending brief to {user_id}: {str(e)}")
                logger.error(f"Unexpected error sending brief to {user_id}: {str(e)}")
                failure_count += 1
        
        print(f"Completed sending weekly briefs: {success_count} successful, {failure_count} failed")
        logger.info(f"Completed sending weekly briefs: {success_count} successful, {failure_count} failed")
        
    except Exception as e:
        print(f"Critical error: {e}")
        logger.critical(f"Critical error: {e}")

# Entry point
if __name__ == "__main__":
    import sys
    
    # Check for CSV file argument
    if len(sys.argv) < 2:
        print("Usage: python weekly_brief.py path_to_csv_file.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    print(f"Sending weekly briefs using data from {csv_file}")
    
    # Run the send function
    asyncio.run(send_weekly_briefs(csv_file))
    
    print("Weekly brief sending completed. See logs for details.")