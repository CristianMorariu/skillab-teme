import json
import os
from pathlib import Path
from typing import Type

from langchain_core.documents import Document as LCDoc
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from database import transaction
from llm_factory import create_llm
from loaders import load_document
from repositories.chunk_repo import ChunkRepository
from repositories.document_repo import DocumentRepository
from schemas import Contract, Invoice

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

EXTRACTION_PROMPT = (
    "Ești un expert în extracția datelor din documente românești. "
    "Extrage datele structurate din următorul document:\n\n{text}"
)

EXTRACTION_REGISTRY = {
    "factura": {"schema": Invoice, "chunk_for_extraction": False, "chunk_for_storage": False},
    "contract": {"schema": Contract, "chunk_for_extraction": True, "chunk_for_storage": True},
    "csv": {"schema": None, "chunk_for_extraction": False, "chunk_for_storage": True},
}


class ExtractionPipeline:
    def __init__(self, provider: str | None = None):
        self.llm = create_llm(provider or os.getenv("LLM_PROVIDER", "ollama"))
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""],
        )
        self._embed_model: SentenceTransformer | None = None

    @property
    def embed_model(self) -> SentenceTransformer:
        if self._embed_model is None:
            self._embed_model = SentenceTransformer(MODEL_NAME)
        return self._embed_model

    def _extract(self, text: str, schema: Type[BaseModel]) -> BaseModel:
        prompt = EXTRACTION_PROMPT.format(text=text)
        return self.llm.with_structured_output(schema).invoke(prompt)

    def _save_json(self, data: BaseModel, doc_type: str) -> None:
        out = Path("extracted_data") / doc_type
        out.mkdir(parents=True, exist_ok=True)
        numar = getattr(data, "numar", "doc").replace("/", "_")
        with open(out / f"{numar}.json", "w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)

    def process(self, file_path: str | Path, doc_type: str) -> BaseModel:
        file_path = Path(file_path)
        config = EXTRACTION_REGISTRY[doc_type]

        # 1. Load
        text = load_document(file_path)

        # 2. Chunk pentru RAG — facturi mici: un singur chunk; contracte: split normal
        if config["chunk_for_storage"]:
            chunks = self.splitter.split_documents([LCDoc(page_content=text)])
            chunk_texts = [c.page_content for c in chunks]
        else:
            chunk_texts = [text]

        # 3. Extract — sărit pentru tipuri fără schemă (ex: csv)
        if config["schema"] is not None:
            extraction_text = (
                "\n\n".join(chunk_texts[:3])
                if config["chunk_for_extraction"] and len(text) > 4000
                else text
            )
            extracted = self._extract(extraction_text, config["schema"])
            self._save_json(extracted, doc_type)
            extracted_meta = extracted.model_dump()
        else:
            extracted = None
            extracted_meta = {}

        # 4. Embed + salvare în DB (atomic)
        embeddings = self.embed_model.encode(chunk_texts, convert_to_numpy=True)

        with transaction() as db:
            doc_repo = DocumentRepository(db)
            chunk_repo = ChunkRepository(db)

            doc = doc_repo.create(
                filename=file_path.name,
                content=text,
                metadata={"doc_type": doc_type, "extracted": extracted_meta},
            )

            chunk_repo.create_chunks_batch(
                [
                    {
                        "document_id": doc.id,
                        "content": chunk_texts[i],
                        "chunk_index": i,
                        "embedding": embeddings[i].tolist(),
                    }
                    for i in range(len(chunk_texts))
                ]
            )

        return extracted
