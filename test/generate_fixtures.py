"""Generates the PDF fixtures used by the test suite. Run once:

    python tests/fixtures/generate_fixtures.py

Fixtures are generated rather than committed as opaque binaries so a
reviewer can see exactly what each test PDF contains (see testing.md
Section 4).
"""

from pathlib import Path

from reportlab.pdfgen import canvas
from pypdf import PdfWriter

FIXTURES_DIR = Path(__file__).parent


def generate_valid_lecture_pdf():
    """A real, text-extractable PDF — the happy-path fixture."""
    path = FIXTURES_DIR / "valid_lecture.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Lecture 4: Introduction to Thermodynamics")
    c.drawString(72, 690, "The first law of thermodynamics states that energy")
    c.drawString(72, 670, "cannot be created or destroyed, only transformed from")
    c.drawString(72, 650, "one form to another within an isolated system.")
    c.drawString(72, 620, "The second law introduces the concept of entropy: in")
    c.drawString(72, 600, "any isolated system, entropy never decreases over time.")
    c.showPage()
    c.save()
    print(f"Wrote {path}")


def generate_scanned_blank_pdf():
    """A structurally valid PDF with zero extractable text — simulates a
    scanned/image-only PDF without needing real OCR/image assets."""
    path = FIXTURES_DIR / "scanned_blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    print(f"Wrote {path}")


if __name__ == "__main__":
    generate_valid_lecture_pdf()
    generate_scanned_blank_pdf()
