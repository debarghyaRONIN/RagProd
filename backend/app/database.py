from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create async engine
# Note: For SQLite in testing, we might need poolclass=StaticPool, but we expect Postgresql (asyncpg) here.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800
)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base class for models
class Base(DeclarativeBase):
    pass

# DB Dependency helper (moved here or in dependencies.py; let's keep it here or import it)
async def get_db_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
