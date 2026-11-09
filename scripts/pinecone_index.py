"""Create a CLASSIC dense serverless index and PROVE it accepts vector writes.

Run:  python scripts/create_pinecone_index.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pinecone
from pinecone import Pinecone, ServerlessSpec

from app.core.config import get_settings

INDEX_NAME = "rag-knowledge-base"


def main() -> None:
    print("pinecone SDK:", pinecone.__version__)
    cfg = get_settings().pinecone
    if not cfg.api_key or not cfg.api_key.get_secret_value():
        raise SystemExit("PINECONE_API_KEY is missing in .env")

    pc = Pinecone(api_key=cfg.api_key.get_secret_value())

    existing = {i["name"] for i in pc.list_indexes()}
    if INDEX_NAME in existing:
        print(f"'{INDEX_NAME}' already exists — verifying it")
    else:
        print(
            f"Creating '{INDEX_NAME}': dim={cfg.dimension}, metric=cosine, "
            f"cloud={cfg.cloud}, region={cfg.region}"
        )
        pc.create_index(
            name=INDEX_NAME,
            dimension=cfg.dimension,  # 1024 -> matches cohere/embed-v4.0
            metric="cosine",
            spec=ServerlessSpec(cloud=cfg.cloud, region=cfg.region),
        )

    # wait until ready
    # FIXED: Pinecone SDK v10+ returns an IndexModel object, not a dict.
    # Use attribute access (desc.status.ready) instead of desc.get("status", {}).get("ready").
    for _ in range(60):
        desc = pc.describe_index(INDEX_NAME)
        # desc is an IndexModel — access via attributes
        status = getattr(desc, "status", None)
        if status is not None and getattr(status, "ready", False):
            break
        time.sleep(2)
    else:
        raise SystemExit("Index did not become ready in time")

    # --- verification 1: shape of the description ---
    # Convert IndexModel to dict for key inspection
    desc_dict = desc.model_dump() if hasattr(desc, "model_dump") else vars(desc)
    keys = sorted(desc_dict.keys())
    print("description keys:", keys)
    if any(k in keys for k in ("embed", "schema", "model")):
        raise SystemExit(
            "❌ This is a DOCUMENT-SCHEMA index, not a classic vectors index. "
            "Delete it and rerun this script."
        )

    # --- verification 2: an actual write/delete roundtrip ---
    # FIXED: Use attribute access for host instead of desc["host"]
    host = desc.host
    idx = pc.Index(host=host)
    try:
        idx.upsert(
            vectors=[
                {
                    "id": "probe-1",
                    "values": [0.0] * cfg.dimension,
                    "metadata": {"probe": True},
                }
            ]
        )
        idx.delete(ids=["probe-1"])
    except Exception as e:
        raise SystemExit(f"❌ Write probe FAILED — index is not classic: {e}")

    print(f"\n✅ Classic index verified — writes work.\nHost for .env:\n{host}")


if __name__ == "__main__":
    main()
