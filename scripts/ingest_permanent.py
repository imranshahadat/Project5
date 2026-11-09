"""Permanent ingestion script. Does NOT clean up vectors or S3 files."""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.application.services.ingestion import process_s3_key
from app.application.dependencies.providers import (
    get_storage,
    build_document_repository,
    get_db_session,
)
from app.core.exceptions import FileValidationError


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.ingest_permanent <path_to_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    filename = file_path.name
    title = file_path.stem
    data = file_path.read_bytes()

    print(f"📄 Preparing to ingest: {filename}")

    # 1. Create DB record
    with get_db_session() as session:
        repo = build_document_repository(session)
        metadata = {"tenant_id": "public", "filename": filename}
        doc_id = repo.add(title=title, content="", source=None, metadata=metadata)
        session.commit()

    # 2. Upload to S3
    s3_key = f"documents/{doc_id}/{filename}"
    print(f"☁️ Uploading to S3: {s3_key}")
    storage = get_storage()
    storage.put(s3_key, data, content_type="application/pdf")

    # 3. Link S3 key to DB
    with get_db_session() as session:
        repo = build_document_repository(session)
        repo.set_source(doc_id, s3_key)
        session.commit()

    print(f"✅ Database updated. Starting background ingestion for: {doc_id}")

    # 4. Run ingestion (this chunks, embeds, and upserts to Pinecone permanently)
    try:
        process_s3_key(s3_key)
        print(
            f"🎉 SUCCESS: Document '{title}' is now permanently in your vector store!"
        )
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")


if __name__ == "__main__":
    main()
