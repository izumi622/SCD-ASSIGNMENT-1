import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment variables BEFORE importing app
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TRIAGE_PROVIDER"] = "simulated"
os.environ["RATE_LIMIT_PER_MINUTE"] = "100"

from app.core.database import get_db_session
from app.main import app
from app.models.db import Base
from app.providers.cache import CacheProvider, get_cache_provider
from app.providers.triage.simulated import SimulatedTriage
from app.services.triage import TriageService, get_triage_service

# Create isolated in-memory SQLite engine for tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initializes tables before each test and drops them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Yields a test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def test_cache():
    """Provides an isolated cache instance with instantaneous in-memory operation."""
    return CacheProvider(redis_url="none")


@pytest.fixture
def test_simulated_triage():
    """Provides a fresh SimulatedTriage instance."""
    return SimulatedTriage()


@pytest.fixture
def test_triage_service(test_simulated_triage, test_cache):
    """Provides a TriageService wired to SimulatedTriage."""
    return TriageService(provider=test_simulated_triage, cache=test_cache)


@pytest.fixture
async def client(db_session, test_cache, test_triage_service):
    """Async HTTP test client with overridden dependencies."""

    async def override_get_db():
        yield db_session

    async def override_get_cache():
        return test_cache

    def override_get_triage():
        return test_triage_service

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_cache_provider] = override_get_cache
    app.dependency_overrides[get_triage_service] = override_get_triage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
