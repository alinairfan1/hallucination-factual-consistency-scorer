from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from scorer.config import settings


def make_session_factory(database_url: str) -> sessionmaker:
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = make_session_factory(settings.database_url)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
