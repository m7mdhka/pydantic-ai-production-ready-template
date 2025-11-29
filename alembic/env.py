import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import src.models
from alembic import context
from src.core.config import settings
from src.database.database import Base

target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """Helps Alembic decide which database objects to track.
    Returns False if the object should be ignored.
    """
    if type_ == "table" and name and name.startswith("LiteLLM"):
        return False

    return True

def do_run_migrations(connection):
    context.configure(
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=target_metadata.schema,
        include_object=include_object
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_async_engine(
        settings.database_url.unicode_string(),
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


asyncio.run(run_migrations_online())
