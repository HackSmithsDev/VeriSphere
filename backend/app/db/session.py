# backend/app/db/session.py
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/verisphere")

# Create a robust, long-lived connection pool optimized for asynchronous operations
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Automatically recycles dead connections safely
    echo=False
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding thread-safe transaction sessions to API routes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise