"""
Generates sample PDF documents for testing the RAG pipeline.
Creates fake but realistic financial PDFs for testing.
 The generated documents are split into two groups:
        - PUBLIC_DOCS: 10-K filings with access_level="all" (anyone can see)
        - CONFIDENTIAL_DOCS: Internal memos with access_level="admin" (restricted)

"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from config.settings import Settings


class SampleDocumentGenerator:
    PUBLIC_DOCS = [
        (
            "tesla_10k.pdf",
            "Tesla, Inc. 2023 Form 10-K",
            "Revenue: $96.8 Billion\n"
            "Net Income: $15.0 Billion\n"
            "Cash at end of year: $29.1 Billion\n"
            "Summary: Tesla continues to lead the EV market with record production.",
        ),
        (
            "apple_10k.pdf",
            "Apple Inc. 2023 Form 10-K",
            "Revenue: $383.3 Billion\n"
            "Net Income: $97.0 Billion\n"
            "Services Revenue: $85.2 Billion\n"
            "Summary: Strong growth in iPhone and Services despite global headwinds.",
        ),
        (
            "nvidia_10k.pdf",
            "NVIDIA Corp 2023 Form 10-K",
            "Revenue: $27.0 Billion\n"
            "Data Center Revenue: $15.0 Billion\n"
            "Gross Margin: 56.9%\n"
            "Summary: AI-driven demand for H100 GPUs is accelerating data center growth.",
        ),
    ]

    CONFIDENTIAL_DOCS = [
        (
            "q4_strategy.pdf",
            "CONFIDENTIAL: Q4 Market Strategy",
            "RESTRICTED ACCESS: INTERNAL ONLY\n"
            "Plan: We are targeting a 15% workforce reduction in underperforming regions.\n"
            "New Project: 'Project Phoenix' involves acquiring a stealth AI startup in Europe.",
        ),
        (
            "ceo_memo.pdf",
            "CONFIDENTIAL: Memo from the CEO",
            "DO NOT DISTRIBUTE\n"
            "Our internal forecast suggests a 20% dip in hardware sales next quarter.\n"
            "We are prioritizing the transition to a subscription-only model for Enterprise software.",
        ),
        (
            "legal_update.pdf",
            "CONFIDENTIAL: Legal Dept - Pending Litigation",
            "PRIVILEGED INFORMATION\n"
            "Update on the patent dispute: We are preparing a $500M settlement fund.\n"
            "Impact: This may affect our dividend payout for the upcoming fiscal year.",
        ),
    ]

    def __init__(self, settings: Settings):
        """Initialize with settings that specify output directories.

        Args:
            settings: Must include ``data_public_dir`` and ``data_confidential_dir``.
        """
        self.settings = settings

    def generate(self) -> None:
        """Create all sample PDFs in the configured data directories.

        Creates the directories if they don't exist, then writes 3 public
        and 3 confidential PDFs. Safe to call multiple times — overwrites
        existing files.
        """
        os.makedirs(self.settings.data_public_dir, exist_ok=True)
        os.makedirs(self.settings.data_confidential_dir, exist_ok=True)

        for filename, title, body in self.PUBLIC_DOCS:
            path = os.path.join(self.settings.data_public_dir, filename)
            self.create_pdf(path, title, body)

        for filename, title, body in self.CONFIDENTIAL_DOCS:
            path = os.path.join(self.settings.data_confidential_dir, filename)
            self.create_pdf(path, title, body)

        print(f"Sample PDFs created in {self.settings.data_public_dir} "
              f"and {self.settings.data_confidential_dir}")

    @staticmethod
    def create_pdf(filepath: str, title: str, content: str) -> None:
        """Write a single PDF file with a title and body text.

        Uses ReportLab to create a simple single-page PDF. Nothing fancy —
        just enough for the RAG pipeline to parse.

        Args:
            filepath: Full path where the PDF will be saved.
            title: Bold heading at the top of the page.
            content: Body text, split on newlines.
        """
        c = canvas.Canvas(filepath, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, title)
        c.setFont("Helvetica", 12)

        y = 720
        for line in content.split("\n"):
            c.drawString(100, y, line)
            y -= 20
        c.save()
