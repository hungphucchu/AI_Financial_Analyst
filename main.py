"""
CLI entry point. Run one of:
    python main.py generate   — create sample PDFs
    python main.py ingest     — embed PDFs into ChromaDB
    python main.py peek       — inspect what's in the vector store
    python main.py chat       — interactive terminal chat
    python main.py serve      — start the FastAPI web server
"""

import sys
from config.settings import Settings
from ingestion.sample_document_generator import SampleDocumentGenerator
from ingestion.ingestion_pipeline import IngestionPipeline
from database.chroma_manager import ChromaManager
from agent.financial_analyst_agent import FinancialAnalystAgent


def cmd_generate(settings: Settings) -> None:
    generator = SampleDocumentGenerator(settings)
    generator.generate()


def cmd_ingest(settings: Settings) -> None:
    pipeline = IngestionPipeline(settings)
    pipeline.run()


def cmd_peek(settings: Settings) -> None:
    db = ChromaManager(settings)
    db.peek()


def cmd_chat(settings: Settings) -> None:
    agent = FinancialAnalystAgent(settings)
    current_role = "intern"

    print("=" * 60)
    print("  FINANCIAL ANALYST AGENT — Interactive Mode")
    print("  Commands:")
    print("    role:admin   — switch to admin role")
    print("    role:intern  — switch to intern role")
    print("    quit         — exit")
    print("=" * 60)

    while True:
        try:
            user_input = input(f"\n[{current_role}] Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        if user_input.startswith("role:"):
            current_role = user_input.split(":")[1].strip()
            print(f"  Switched to role: {current_role}")
            continue

        answer = agent.run(user_input, role=current_role)
        print(f"\n{'─'*60}")
        print(f"Answer:\n{answer}")
        print(f"{'─'*60}")


def cmd_serve(settings: Settings) -> None:
    import uvicorn
    from api.financial_analyst_api import FinancialAnalystAPI

    api = FinancialAnalystAPI(settings)
    print(f"Starting server on http://{settings.api_host}:{settings.api_port}")
    uvicorn.run(api.app, host=settings.api_host, port=settings.api_port)


COMMANDS = {
    "generate": cmd_generate,
    "ingest": cmd_ingest,
    "peek": cmd_peek,
    "chat": cmd_chat,
    "serve": cmd_serve,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    settings = Settings.from_env()
    COMMANDS[sys.argv[1]](settings)


if __name__ == "__main__":
    main()
