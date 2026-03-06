"""
ASGI entry point for Uvicorn and Cloud Run.

Why this is separate from main.py:
    main.py is the CLI entry point — importing it would boot up argparse
    and register CLI commands even when we just want to start the web server.
    This file only creates the FastAPI app, nothing else.

Usage (local):
    uvicorn server:app --host 0.0.0.0 --port 8000

Usage (Docker / Cloud Run):
    The Dockerfile CMD runs: uvicorn server:app --host 0.0.0.0 --port $PORT
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

try:
    from config.settings import Settings
    from api.financial_analyst_api import FinancialAnalystAPI

    settings = Settings.from_env()
    api = FinancialAnalystAPI(settings)
    app = api.app
    logger.info("Application initialized successfully")

except Exception as e:
    logger.error("FATAL: Failed to initialize application: %s", e, exc_info=True)

    from fastapi import FastAPI
    app = FastAPI()
    startup_error = str(e)

    @app.get("/health")
    def health():
        return {"status": "error", "detail": startup_error}

    @app.get("/")
    def root():
        return {"status": "error", "detail": startup_error}
