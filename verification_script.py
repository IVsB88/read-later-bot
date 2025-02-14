# verification_script.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from config.config import Config
from models_dir.models import Base, User, Link, Reminder, UserAnalytics

def verify_schema(database_url=None):
    """Verify database schema and structure"""
    print("\n=== Database Schema Verification ===\n")
    
    try:
        # Use provided URL or get from config
        if not database_url:
            config = Config()
            database_url = config.DATABASE_URL
            print(f"Environment: {config.ENVIRONMENT}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create inspector
        inspector = inspect(engine)
        
        # Check each table
        tables = inspector.get_table_names()
        print(f"\nFound {len(tables)} tables:")
        
        for table in tables:
            print(f"\nTable: {table}")
            
            # Get columns
            print("Columns:")
            for column in inspector.get_columns(table):
                print(f"  - {column['name']}: {column['type']} (nullable: {column['nullable']})")
            
            # Get foreign keys
            print("Foreign Keys:")
            for fk in inspector.get_foreign_keys(table):
                print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
            # Get indexes
            print("Indexes:")
            for idx in inspector.get_indexes(table):
                print(f"  - {idx['name']}: {idx['column_names']}")
        
        print("\n✅ Schema verification completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        return False

def verify_test_schema():
    """Verify schema using test database"""
    print("\n=== Test Database Schema Verification ===\n")
    
    try:
        # Create test database
        test_url = "sqlite:///:memory:"
        engine = create_engine(test_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Verify schema
        success = verify_schema(test_url)
        
        # Cleanup
        Base.metadata.drop_all(engine)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Error during test verification: {str(e)}")
        return False

def check_data(database_url=None):
    """Check actual data in database"""
    print("\n=== Database Data Verification ===\n")
    
    try:
        # Use provided URL or get from config
        if not database_url:
            config = Config()
            database_url = config.DATABASE_URL
        
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Check each table's data
            user_count = session.query(User).count()
            link_count = session.query(Link).count()
            reminder_count = session.query(Reminder).count()
            analytics_count = session.query(UserAnalytics).count()
            
            print("Record Counts:")
            print(f"- Users: {user_count}")
            print(f"- Links: {link_count}")
            print(f"- Reminders: {reminder_count}")
            print(f"- Analytics: {analytics_count}")
            
            # Check last entries
            if link_count > 0:
                last_link = session.query(Link).order_by(Link.id.desc()).first()
                print(f"\nLast Link: ID={last_link.id}, URL={last_link.url}")
            
            if reminder_count > 0:
                last_reminder = session.query(Reminder).order_by(Reminder.id.desc()).first()
                print(f"Last Reminder: ID={last_reminder.id}, Link ID={last_reminder.link_id}")
            
            print("\n✅ Data verification completed successfully")
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"\n❌ Error during data verification: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    # Check if test mode is requested
    test_mode = "--test" in sys.argv
    
    if test_mode:
        print("Running in test mode...")
        success = verify_test_schema()
    else:
        print("Running in normal mode...")
        success = verify_schema() and check_data()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)