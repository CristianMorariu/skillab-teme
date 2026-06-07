from typing import Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import func
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session

from models import Document


class DocumentRepository:
    _UPDATABLE = {"filename", "content", "doc_metadata"}

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, filename: str, content: str, metadata: dict[str, Any]) -> Document:
        doc = Document(filename=filename, content=content, doc_metadata=metadata)
        self.db.add(doc)
        self.db.flush()
        self.db.refresh(doc)
        return doc

    def get_by_id(self, doc_id: int) -> Document | None:
        return self.db.get(Document, doc_id)

    def get_by_filename(self, filename: str) -> Document | None:
        return self.db.query(Document).filter(Document.filename == filename).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        return (
            self.db.query(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(func.count(Document.id)).scalar()

    def update(self, doc_id: int, **fields: Any) -> Document | None:
        clean = {k: v for k, v in fields.items() if k in self._UPDATABLE}
        if not clean:
            return self.db.get(Document, doc_id)
        self.db.execute(
            sql_update(Document).where(Document.id == doc_id).values(**clean)
        )
        return self.db.get(Document, doc_id)

    def delete(self, doc_id: int) -> bool:
        result = self.db.execute(sql_delete(Document).where(Document.id == doc_id))
        return result.rowcount > 0
