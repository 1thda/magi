import io

from reportlab.pdfgen import canvas

from extract import extract_text


def _make_pdf_with_text(text: str) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, text)
    c.save()
    buf.seek(0)
    return buf


def _make_blank_pdf() -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def test_extract_text_returns_text_content():
    pdf = _make_pdf_with_text("Hello Research World")
    result = extract_text(pdf)
    assert "Hello Research World" in result


def test_extract_text_returns_empty_for_blank_pdf():
    pdf = _make_blank_pdf()
    result = extract_text(pdf)
    assert result == ""
