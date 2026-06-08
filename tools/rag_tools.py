from database import transaction
from rag_service import RAGService

from .params_models import SearchDocumentsParams
from .registry import register_tool


@register_tool
def search_documents(params: SearchDocumentsParams) -> str:
    """Caută informații relevante în documentele încărcate (facturi, contracte). Folosește acest tool când întrebarea se referă la documente, clauze, valori sau date din documente."""
    with transaction() as db:
        rag = RAGService(db)
        context = rag.get_context(params.query, top_k=7, threshold=0.0)
    if not context:
        return "Nu am găsit informații relevante în documentele disponibile."
    return context
