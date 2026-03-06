#!/bin/sh
# Bootstrap data on first run (if ChromaDB is empty), then start the server.
# Subsequent runs skip this because chroma_data volume persists.

if [ ! -d "/app/chroma_db/chroma.sqlite3" ] && [ ! -f "/app/chroma_db/chroma.sqlite3" ]; then
    echo "=== First run: generating sample data and ingesting ==="
    python main.py generate
    python main.py ingest
    echo "=== Data bootstrap complete ==="
fi

echo "Starting server on port ${PORT:-8000}..."
exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
