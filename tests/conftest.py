"""Pytest configuration and fixtures for testing."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your application and models here
# from core.db.session import Base, get_db
# from main import app


# Fixture for a temporary directory
@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing and clean up after."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# Fixture for a test database
@pytest.fixture(scope="session")
def test_db() -> Generator[str, None, None]:
    """Create a test database and yield the connection string."""
    # Use SQLite in-memory database for testing
    TEST_DATABASE_URL = "sqlite:///:memory:"
    
    # Create test database and tables
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    # Base.metadata.create_all(bind=engine)
    
    yield TEST_DATABASE_URL
    
    # Clean up
    # Base.metadata.drop_all(bind=engine)
    engine.dispose()


# Fixture for a database session
@pytest.fixture
def db_session(test_db: str) -> Generator[sessionmaker, None, None]:
    """Create a new database session with a rollback at the end of the test."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(test_db)
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# Fixture for the FastAPI test client
@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    # Override dependencies for testing
    # app.dependency_overrides[get_db] = override_get_db
    
    # with TestClient(app) as client:
    #     yield client
    pass


# Fixture for test configuration
@pytest.fixture
def test_config() -> dict:
    """Return a test configuration dictionary."""
    return {
        "TESTING": True,
        "DEBUG": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    }
