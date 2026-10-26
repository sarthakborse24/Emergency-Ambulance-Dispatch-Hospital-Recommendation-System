"""
Pytest configuration and shared fixtures using in-memory SQLite database.
Ensures tests run in complete isolation without modifying production or demo data.
"""

import pytest
from app import create_app
from config import TestingConfig
from database import init_db, get_session
from seed_data import seed_database


@pytest.fixture(scope="session")
def app():
    """Create test application instance with in-memory database."""
    test_app = create_app(TestingConfig)
    return test_app


@pytest.fixture(scope="function")
def db_session(app):
    """Provide isolated database session populated with seed test dataset."""
    engine = init_db("sqlite:///:memory:")
    session = get_session()
    seed_database(session)
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(app, db_session):
    """Flask test client connected to the isolated in-memory test database."""
    with app.test_client() as test_client:
        yield test_client
