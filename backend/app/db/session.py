from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
# Disable asyncpg statement cache if using pooled endpoint or cloud provider (Neon, Render, Supabase)
if (
    "6543" in settings.DATABASE_URL
    or "ssl" in settings.DATABASE_URL
    or "render.com" in settings.DATABASE_URL
    or "dpg-" in settings.DATABASE_URL
):
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

AsyncSessionLocal = async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
