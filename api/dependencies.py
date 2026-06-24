from contextlib import contextmanager
from app.db import get_db_connection


@contextmanager
def get_db_context():
    db = get_db_connection()
    try:
        yield db
    finally:
        db.close()
