from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from payment_lab.core.config import settings
from payment_lab.db.models import Base
import sentinelqa.db.models  # noqa: F401 - Register SentinelQA models with metadata

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize tables in database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
