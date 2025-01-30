from logging.config import fileConfig
import sys
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add your project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your configuration and models
from config.config import Config
from models_dir.models import Base

# Create your application config instance
app_config = Config()  # Renamed to avoid confusion
app_config.validate_config()

# Get Alembic config object
alembic_cfg = context.config

# Override sqlalchemy.url with your application's DATABASE_URL
alembic_cfg.set_main_option('sqlalchemy.url', app_config.DATABASE_URL)

# Setup Python logging configuration
if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Set SQLAlchemy metadata for migrations
target_metadata = Base.metadata
print("Available tables in metadata:")
for table_name in target_metadata.tables.keys():
    print(f"- {table_name}")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()