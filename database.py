"""
Database connection and session management module using SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import Config

Base = declarative_base()

_engine = None
_session_factory = None
SessionLocal = None


def init_db(database_uri=None):
    """Initialize database engine, session factory, and create tables."""
    global _engine, _session_factory, SessionLocal
    
    uri = database_uri or Config.SQLALCHEMY_DATABASE_URI
    
    # SQLite-specific connect args
    connect_args = {"check_same_thread": False} if uri.startswith("sqlite") else {}
    
    _engine = create_engine(uri, connect_args=connect_args, echo=False)
    _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    SessionLocal = scoped_session(_session_factory)
    
    # Import all models to register with Base.metadata
    import models  # noqa: F401
    Base.metadata.create_all(bind=_engine)
    return _engine


def get_session():
    """Obtain a new thread-safe database session, initializing engine if needed."""
    global SessionLocal
    if SessionLocal is None:
        init_db()
    return SessionLocal()


def get_db():
    """Generator for use with context managers or request dependencies."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
