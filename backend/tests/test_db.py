
"""Tests for database session wiring."""

from app import db


def test_get_db_uses_temporary_test_engine(client):
    """The client fixture must bind get_db() to its temporary engine."""
    assert db.SessionLocal.kw["bind"] is db.engine

    generator = db.get_db()
    session = next(generator)

    try:
        assert session.get_bind() is db.engine
    finally:
        generator.close()