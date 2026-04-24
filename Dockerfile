# Stage 1: Builder — installs dependencies in a temp container.
# This stage gets thrown away after build, keeping the final image small.
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
# --no-cache-dir: skip pip cache (smaller image)
# --prefix=/install: install to a separate folder so we can copy just the packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production — only contains installed packages + source code.
# No pip cache, no build tools → ~400MB instead of ~1.2GB.
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage into the production image
COPY --from=builder /install /usr/local

# Copy only the source code folders needed to run the app
COPY config/ config/
COPY database/ database/
COPY ingestion/ ingestion/
COPY tools/ tools/
COPY agent/ agent/
COPY api/ api/
COPY static/ static/
COPY main.py .
COPY server.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Cloud Run sets PORT automatically, default to 8000 for local
ENV PORT=8000

EXPOSE ${PORT}

# Bootstrap data on first run, then start uvicorn
CMD ["./entrypoint.sh"]
