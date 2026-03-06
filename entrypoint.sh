#!/bin/sh
# Start uvicorn FIRST so Cloud Run sees the port open immediately.
# Then bootstrap data in the background if this is a fresh container.
# Cloud Run kills containers that don't bind to $PORT within the startup timeout.

PORT="${PORT:-8000}"

if [ ! -d "/app/chroma_db/chroma.sqlite3" ] && [ ! -f "/app/chroma_db/chroma.sqlite3" ]; then
    echo "=== First run detected: will bootstrap data after server starts ==="

    # Start uvicorn in the background so the port opens right away
    uvicorn server:app --host 0.0.0.0 --port "$PORT" &
    SERVER_PID=$!

    # Give uvicorn a moment to bind the port
    sleep 3

    # Now generate and ingest sample data
    echo "=== Generating sample data ==="
    python main.py generate
    echo "=== Ingesting into ChromaDB ==="
    python main.py ingest
    echo "=== Data bootstrap complete ==="

    # Keep the container alive by waiting on the server process
    wait $SERVER_PID
else
    echo "Starting server on port ${PORT}..."
    exec uvicorn server:app --host 0.0.0.0 --port "$PORT"
fi
