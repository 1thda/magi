from pypdf import PdfReader


def extract_text(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text).strip()
