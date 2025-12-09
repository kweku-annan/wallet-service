"""
Pytest configuration and shared fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, AsyncMock, patch
from app.database import Base, get_db
from app.main import app
from app.core.config import Settings, get_settings


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh database for each test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    Create a test client with database dependency override.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings():
    """
    Mock settings with test credentials.
    """
    return Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="test-secret-key-for-testing-only",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        GOOGLE_CLIENT_ID="test-client-id",
        GOOGLE_CLIENT_SECRET="test-client-secret",
        GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback",
        PAYSTACK_SECRET_KEY="test-paystack-secret",
        PAYSTACK_PUBLIC_KEY="test-paystack-public",
        PAYSTACK_WEBHOOK_URL="http://localhost:8000/wallet/paystack/webhook",
        APP_NAME="Wallet Service Test",
        DEBUG=True,
    )


@pytest.fixture
def mock_settings_no_client_id():
    """
    Mock settings with missing GOOGLE_CLIENT_ID.
    """
    return Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="test-secret-key-for-testing-only",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        GOOGLE_CLIENT_ID="",  # Empty client ID
        GOOGLE_CLIENT_SECRET="test-client-secret",
        GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback",
        PAYSTACK_SECRET_KEY="test-paystack-secret",
        PAYSTACK_PUBLIC_KEY="test-paystack-public",
        PAYSTACK_WEBHOOK_URL="http://localhost:8000/wallet/paystack/webhook",
        APP_NAME="Wallet Service Test",
        DEBUG=True,
    )


@pytest.fixture
def mock_settings_no_client_secret():
    """
    Mock settings with missing GOOGLE_CLIENT_SECRET.
    """
    return Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="test-secret-key-for-testing-only",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        GOOGLE_CLIENT_ID="test-client-id",
        GOOGLE_CLIENT_SECRET="",  # Empty client secret
        GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback",
        PAYSTACK_SECRET_KEY="test-paystack-secret",
        PAYSTACK_PUBLIC_KEY="test-paystack-public",
        PAYSTACK_WEBHOOK_URL="http://localhost:8000/wallet/paystack/webhook",
        APP_NAME="Wallet Service Test",
        DEBUG=True,
    )


@pytest.fixture
def mock_oauth_client():
    """
    Mock OAuth client for testing.
    """
    mock_client = Mock()
    mock_client.authorize_redirect = AsyncMock()
    return mock_client
