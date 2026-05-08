from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_ENGINES_BY_URL = {}


def _engine_for_url(database_url: str):
    engine = _ENGINES_BY_URL.get(database_url)
    if engine is None:
        engine = create_engine(database_url, future=True, pool_pre_ping=True)
        _ENGINES_BY_URL[database_url] = engine
    return engine


def get_engine():
    return _engine_for_url(get_settings().database_url)


def get_db():
    session_local = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def reset_engine_cache() -> None:
    for engine in _ENGINES_BY_URL.values():
        engine.dispose()
    _ENGINES_BY_URL.clear()
