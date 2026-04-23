import fitz  # PyMuPDF
from docx import Document
import easyocr
import io
from PIL import Image
from typing import Optional

class DocumentProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])

    def extract_text(self, file_bytes: bytes, filename: str) -> Optional[str]:
        if filename.lower().endswith('.pdf'):
            return self._extract_pdf(file_bytes)
        elif filename.lower().endswith('.docx'):
            return self._extract_docx(file_bytes)
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            return self._extract_image(file_bytes)
        else:
            raise ValueError("Unsupported file type")

    def _extract_pdf(self, file_bytes: bytes) -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def _extract_docx(self, file_bytes: bytes) -> str:
        doc = Document(io.BytesIO(file_bytes))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text

    def _extract_image(self, file_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(file_bytes))
        results = self.reader.readtext(image)
        text = " ".join([result[1] for result in results])
        return text