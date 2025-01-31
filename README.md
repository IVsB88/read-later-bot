# Read Complete Bot

A Telegram bot for saving links and getting reminders to read them later. The bot allows users to save URLs and schedules automatic reminders to ensure links are read.

## Core Features
- Save links via Telegram messages
- Smart reminder scheduling:
  * Default: Next day at 9 AM user's local time
  * Custom: User can choose tomorrow/2 days/3 days
- Timezone management for accurate reminder timing
- Snooze function: "Remind me tomorrow" option
- Analytics tracking:
  * Links saved
  * Reminder completion rates
  * Snooze patterns
  * User engagement metrics

## Technical Requirements
- Python 3.12
- PostgreSQL 15+
- Telegram Bot Token (get from @BotFather)
- Free port for local development (default: 5432 for PostgreSQL)

## Local Development Setup
1. **Database Setup**
   - Install PostgreSQL
   - Create database: `readlater_bot`
   - Port: 5432 (default)

2. **Environment Setup**
   - Clone repository
   - Create virtual environment: `python -m venv venv`
   - Activate venv:
     * Windows: `venv\Scripts\activate`
     * Linux/Mac: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`

3. **Configuration**
   - Copy `.env.example` to `.env`
   - Required settings:
     ```
     TELEGRAM_TOKEN=your_bot_token
     DATABASE_URL=postgresql://postgres:your_password@localhost:5432/readlater_bot
     ENVIRONMENT=development
     ```

4. **Database Initialization**
   - Run migrations: `alembic upgrade head`
   - Initialize database: `python init_db.py`

5. **Running the Bot**
   - Start bot: `python src/bot.py`
   - Test by messaging your bot on Telegram

## Important Files
- `src/bot.py`: Main bot logic
- `models_dir/models.py`: Database models
- `config/config.py`: Configuration management
- `database/db_handler.py`: Database operations

## Troubleshooting
Common issues:
- Database connection fails: Check PostgreSQL service is running
- Bot not responding: Verify TELEGRAM_TOKEN in .env
- Reminder timezone issues: Check user has set timezone in bot

## Database Maintenance
- Reset database: `python reset_db.py`
- Verify schema: `python verification_script.py`
- Create new migration: `alembic revision -m "description"`

## Testing
- Run tests: `pytest`
- Test database uses SQLite (no PostgreSQL needed for tests)