

#  install dependencies 
FROM python:3.9-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# production image 
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /install /usr/local

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
