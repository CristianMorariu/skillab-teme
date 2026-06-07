from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models import Document, DocumentChunk


class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_chunks_batch(self, chunks: list[dict]) -> list[DocumentChunk]:
        objects = [DocumentChunk(**c) for c in chunks]
        self.db.add_all(objects)
        self.db.flush()
        return objects

    def get_document_chunks(self, document_id: int) -> list[DocumentChunk]:
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        similarity = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")

        stmt = (
            select(DocumentChunk, similarity)
            .options(joinedload(DocumentChunk.document))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        rows = self.db.execute(stmt).all()
        return [(chunk, float(score)) for chunk, score in rows]
