from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

# Create database engine
# echo=True will log all SQL queries, useful for debugging
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True, # Verify connections before using them
)

# Create a SessionLocal class - each instance will be a database session
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# Base class for our ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function that provides a database session.

    :return:
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()