"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vlm_bench.storage.models import Base

_engines: dict[str, object] = {}
_sessionmakers: dict[str, sessionmaker] = {}


def get_engine(db_path: str | Path = "data/vlm_bench.db"):
    key = str(Path(db_path).resolve())
    if key not in _engines:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _engines[key] = create_engine(f"sqlite:///{path}", echo=False)
        _sessionmakers[key] = sessionmaker(bind=_engines[key], expire_on_commit=False)
    return _engines[key]


def init_db(db_path: str | Path = "data/vlm_bench.db") -> None:
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(db_path: str | Path = "data/vlm_bench.db") -> Generator[Session, None, None]:
    init_db(db_path)
    key = str(Path(db_path).resolve())
    session = _sessionmakers[key]()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
