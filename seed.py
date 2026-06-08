"""
Preîncarcă data sample-urile în DB.
  python seed.py           — skip fișierele deja încărcate
  python seed.py --fresh   — șterge tot și reîncarcă de la zero
"""
import sys
from pathlib import Path

from database import transaction
from pipeline import ExtractionPipeline
from repositories.document_repo import DocumentRepository

SAMPLES = [
    ("data-samples-for-chunking/factura_001.txt", "factura"),
    ("data-samples-for-chunking/factura_002.txt", "factura"),
    ("data-samples-for-chunking/contract_consultanta.txt", "contract"),
    ("data-samples-for-chunking/contract_servicii.txt", "contract"),
    ("data-samples-for-chunking/facturi_export.csv", "csv"),
]


def clear_db() -> None:
    with transaction() as db:
        repo = DocumentRepository(db)
        for doc in repo.get_all():
            repo.delete(doc.id)
    print("[clear] DB golit.")


def already_loaded(filename: str) -> bool:
    with transaction() as db:
        return DocumentRepository(db).get_by_filename(filename) is not None


def run(fresh: bool = False) -> None:
    if fresh:
        clear_db()

    pipeline = ExtractionPipeline()
    for path_str, doc_type in SAMPLES:
        path = Path(path_str)
        if already_loaded(path.name):
            print(f"[skip] {path.name} — deja în DB")
            continue
        try:
            pipeline.process(path, doc_type)
            print(f"[ok]   {path.name} ({doc_type})")
        except Exception as e:
            print(f"[err]  {path.name}: {e}")

    print("Seed complet.")


if __name__ == "__main__":
    run(fresh="--fresh" in sys.argv)
