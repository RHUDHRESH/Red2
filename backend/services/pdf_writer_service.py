from __future__ import annotations

import base64
import io
import logging


logger = logging.getLogger(__name__)


def make_simple_pdf_base64(title: str, body: str) -> str:
    try:
        # Try reportlab for real PDFs
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, title[:100])
        y -= 30
        c.setFont("Helvetica", 11)
        for line in body.split("\n"):
            for chunk in [line[i:i+100] for i in range(0, len(line), 100)]:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 11)
                c.drawString(50, y, chunk)
                y -= 16
        c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as e:
        logger.warning(f"reportlab not available or failed: {e}")
        # Fallback: base64-encoded plain text as .txt disguised for quick download
        data = f"{title}\n\n{body}".encode("utf-8")
        return base64.b64encode(data).decode("ascii")

