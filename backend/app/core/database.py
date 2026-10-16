from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_database() -> None:
    await engine.dispose()