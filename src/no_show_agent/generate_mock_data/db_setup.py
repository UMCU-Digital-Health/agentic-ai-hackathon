"""
Creates a fresh clinic.db from the table definitions in db_models.py.
No manual CREATE TABLE statements here - the schema comes straight from
those classes, so there's exactly one definition of each table.

Run this first, before any of the generate_*.py scripts.
"""

from sqlmodel import Session, SQLModel, create_engine

from no_show_agent.generate_mock_data import (
    db_models,  # noqa: F401  (registers the tables below)
)
from no_show_agent.generate_mock_data.config import DB_PATH

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}")
    return _engine


def get_session() -> Session:
    """expire_on_commit=False so returned rows stay usable after the
    `with` block closes the session, without extra refresh queries."""
    return Session(get_engine(), expire_on_commit=False)


def create_schema():
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print(f"Schema created in {DB_PATH}")


if __name__ == "__main__":
    create_schema()
