"""Pytest configuration for async tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

import app.models.company  # noqa: F401 — register metadata
import app.models.trace  # noqa: F401


@pytest.fixture
async def session() -> AsyncSession:
    """Provide an in-memory async SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create sessionmaker
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as s:
        yield s
    
    await engine.dispose()
