import asyncio
import os
import tempfile
from datetime import datetime, timezone
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from apps.api.main import app
from payment_lab.db.models import Base, Merchant, PaymentMethod
import sentinelqa.db.models  # noqa: F401
from payment_lab.db.session import get_db

TEMP_DB_PATH = os.path.join(tempfile.gettempdir(), "sentinelqa_test_suite.db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEMP_DB_PATH}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30},
)


@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()


async_test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_test_session_factory() as session:
        # Seed merchants: m_active_1, m_active_2, m_inactive_1
        now = datetime.now(timezone.utc)
        m1 = Merchant(id="m_active_1", name="Active Merchant 1", status="ACTIVE", created_at=now)
        m2 = Merchant(id="m_active_2", name="Active Merchant 2", status="ACTIVE", created_at=now)
        m3 = Merchant(id="m_inactive_1", name="Inactive Merchant", status="INACTIVE", created_at=now)
        session.add_all([m1, m2, m3])

        # Seed payment methods
        pm1 = PaymentMethod(id="pm_card_1", merchant_id="m_active_1", type="CARD_TOKEN", token="tok_visa_1234", created_at=now)
        pm2 = PaymentMethod(id="pm_card_2", merchant_id="m_active_2", type="CARD_TOKEN", token="tok_master_5678", created_at=now)
        session.add_all([pm1, pm2])

        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_test_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_test_session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
