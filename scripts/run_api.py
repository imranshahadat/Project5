#!/usr/bin/env python3
"""Launch the FastAPI service with uvicorn.

Usage:
    python scripts/run_api.py                    # 127.0.0.1:8000
    python scripts/run_api.py --host 0.0.0.0 --port 8080 --reload
"""

import argparse
import os
import sys

# bootstrap src/ on path (same pattern as the other scripts)
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _c in (_PARENT, os.path.join(_PARENT, "src")):
    if os.path.isdir(os.path.join(_c, "app")):
        sys.path.insert(0, _c)
        break


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG Chat FastAPI service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="auto-reload on file changes")
    parser.add_argument("--workers", type=int, default=1, help="uvicorn worker count")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
