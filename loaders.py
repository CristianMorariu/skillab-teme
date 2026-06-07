from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)

LOADER_REGISTRY = {
    "pdf": PyPDFLoader,
    "docx": Docx2txtLoader,
    "txt": lambda path: TextLoader(path, autodetect_encoding=True),
    "csv": CSVLoader,
}


def load_document(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lstrip(".").lower()
    if ext not in LOADER_REGISTRY:
        raise ValueError(f"Tip nesuportat: .{ext}")
    docs = LOADER_REGISTRY[ext](str(path)).load()
    return "\n\n".join(d.page_content for d in docs)
