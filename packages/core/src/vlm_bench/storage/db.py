"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vlm_bench.storage.models import Base

_engine = None
_SessionLocal = None


def get_engine(db_path: str | Path = "data/vlm_bench.db"):
    global _engine, _SessionLocal
    if _engine is None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{path}", echo=False)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db(db_path: str | Path = "data/vlm_bench.db") -> None:
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(db_path: str | Path = "data/vlm_bench.db") -> Generator[Session, None, None]:
    init_db(db_path)
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
