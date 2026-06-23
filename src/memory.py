"""
Memory Manager — Repository pattern + PersistentMemory .

Pattern: load_messages → invoke agent → save_message (×2).
Tranzacția e gestionată explicit; DB-ul e cel din proiect (port 5433).
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://demo:demo123@localhost:5433/rag_demo",
)

_engine = create_engine(DB_URL)
SessionFactory = sessionmaker(bind=_engine)


@contextmanager
def unit_of_work():
    """O tranzacție = un context. Commit la succes, rollback la eroare."""
    db: DBSession = SessionFactory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class ChatMessageRepository:
    """Toată logica de DB pentru mesaje, izolată aici."""

    def __init__(self, db: DBSession):
        self.db = db

    def add(self, session_id: str, role: str, content: str) -> None:
        self.db.execute(
            text(
                "INSERT INTO chat_messages (session_id, role, content, created_at) "
                "VALUES (:sid, :role, :content, NOW())"
            ),
            {"sid": session_id, "role": role, "content": content},
        )

    def latest(self, session_id: str, limit: int) -> list[dict]:
        rows = self.db.execute(
            text(
                "SELECT role, content FROM ("
                "  SELECT role, content, created_at, id FROM chat_messages "
                "  WHERE session_id = :sid "
                "  ORDER BY created_at DESC, id DESC "
                "  LIMIT :lim"
                ") sub ORDER BY created_at ASC, id ASC"
            ),
            {"sid": session_id, "lim": limit},
        ).fetchall()
        return [{"role": r.role, "content": r.content} for r in rows]


class PersistentMemory:
    """API curat pentru restul aplicației. Nu știe de SQL."""

    def __init__(self, window: int = 10):
        self.window = window

    def load_messages(self, session_id: str) -> list[dict]:
        with unit_of_work() as db:
            return ChatMessageRepository(db).latest(session_id, self.window)

    def save_message(self, session_id: str, role: str, content: str) -> None:
        with unit_of_work() as db:
            ChatMessageRepository(db).add(session_id, role, content)
