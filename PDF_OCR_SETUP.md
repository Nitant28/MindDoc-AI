# PDF & Image Text Extraction Setup Guide

## Overview
Your MindDoc AI bot now supports:
- ✓ **Text-based PDFs** (direct text extraction)
- ✓ **Image-based PDFs** (scanned documents with OCR)
- ✓ **Mixed PDFs** (both text and images)
- ✓ **Image files** (PNG, JPG, JPEG, TIFF, BMP, GIF)
- ✓ **DOCX files** (Microsoft Word documents)

## Installation & Setup

### 1. Install Python Dependencies
All required packages are in `requirements.txt`. Install them:

```bash
pip install -r requirements.txt
```

### 2. Windows: Install Tesseract OCR (Optional but Recommended)

Tesseract is the primary OCR engine for text-based image documents. EasyOCR is included but Tesseract is more reliable.

#### Option A: Automated Installation (PowerShell)
```powershell
# Download and install Tesseract
$installerUrl = "https://github.com/UB-Mannheim/tesseract/wiki"
Write-Host "Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/releases"
Write-Host "Recommended: tesseract-ocr-w64-setup-v5.x.exe"
Write-Host "During installation, select 'Additional script data' for better accuracy"
```

#### Option B: Manual Installation
1. Download from: https://github.com/UB-Mannheim/tesseract/releases
2. Get the latest `tesseract-ocr-w64-setup-v5.x.exe`
3. Run installer
4. During setup:
   - Install to default location: `C:\Program Files\Tesseract-OCR`
   - Enable "Additional script data" for better language support
5. Add to Python (the code auto-detects at `C:\Program Files\Tesseract-OCR\tesseract.exe`)

#### Option C: Chocolatey
```powershell
choco install tesseract
```

### 3. Configure Tesseract Path (if needed)

If Tesseract is installed in a custom location, add this to your code:

```python
import pytesseract
pytesseract.pytesseract.pytesseract_cmd = r'C:\Custom\Path\To\tesseract.exe'
```

### 4. Verify Installation

Run the test suite to verify everything works:

```bash
python test_pdf_processing.py
```

You should see:
```
DOCUMENT EXTRACTION CAPABILITIES
✓ PyMuPDF (fitz): True
✓ pdfplumber: True
✓ PyPDF2: True
✓ EasyOCR: True
✓ Tesseract OCR: True
✓ DOCX support: True
✓ Unstructured: True
```

## How It Works

### PDF Processing Pipeline
1. **Text Extraction First** - Tries 3 methods (PyMuPDF, pdfplumber, PyPDF2)
2. **Fallback to OCR** - If text extraction yields <20 chars per page, applies OCR
3. **Full OCR** - If all text methods fail, converts entire PDF to images and OCRs
4. **Table Support** - Automatically detects and formats tables

### OCR Engine Priority
1. **EasyOCR** - Best accuracy for complex layouts, handles multiple languages
2. **Tesseract** - Fast, reliable, standard OCR engine
3. **Fallback** - Basic text detection if neither available

## Supported File Types

| Format | Text Extract | OCR Support | Table Support |
|--------|-------------|------------|---------------|
| PDF    | ✓✓✓        | ✓✓         | ✓             |
| DOCX   | ✓✓         | -          | ✓             |
| PNG    | -           | ✓✓         | -             |
| JPG    | -           | ✓✓         | -             |
| TIFF   | -           | ✓✓         | -             |
| BMP    | -           | ✓✓         | -             |
| GIF    | -           | ✓✓         | -             |

## Troubleshooting

### "Tesseract is not installed" Error
**Solution:** Install Tesseract from: https://github.com/UB-Mannheim/tesseract/releases

### Poor OCR Accuracy
**Solutions:**
1. Ensure PDF is not encrypted (update PDF first)
2. Use high-resolution scans (150+ DPI)
3. Try EasyOCR instead (better for handwriting)
4. Preprocess with: `Image.filter(ImageFilter.SHARPEN)`

### EasyOCR Takes Too Long on First Run
**Reason:** Downloads OCR models (~100MB) on first use
**Solution:** Run once in background, then subsequent runs are fast

### "ModuleNotFoundError: No module named 'pytesseract'"
**Solution:**
```bash
pip install pytesseract pillow
```

### PDF Processing Crashes
**Solutions:**
1. Check PDF is valid: `pdfplumber.open(file)` should work
2. Try uploading a smaller PDF first
3. Check logs: `QUICKSTART.md` for debug tips

## Performance Tips

1. **Large PDFs** - Process in chunks if >50MB
2. **Scanned PDFs** - Use 2x zoom (already default)
3. **Multiple Languages** - Configure EasyOCR: `easyocr.Reader(['en', 'es', 'fr'])`
4. **Batch Processing** - Upload documents in sequence, not parallel

## API Usage

### Upload Document with Auto OCR
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

The system will:
1. Extract all text (plain + OCR)
2. Create vector embeddings for search
3. Save chunks for RAG retrieval
4. Return document ID

### Example Response
```json
{
  "message": "Document uploaded",
  "document_id": 42,
  "text_extracted": "2500 characters",
  "pages_processed": 5
}
```

## Advanced Configuration

### Custom OCR Settings

Edit `app/services/document_service.py`:

```python
# Increase PyMuPDF zoom for better OCR
pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))  # 3x instead of 2x

# Configure EasyOCR confidence threshold
if res[2] > 0.5:  # Only use high-confidence results
    text += res[1]
```

### Multi-Language OCR

```python
easyocr_reader = easyocr.Reader(['en', 'es', 'fr', 'de', 'zh'])
```

## Production Deployment

For Windows Server or Docker:

```dockerfile
# Dockerfile with Tesseract
FROM python:3.11
RUN apt-get update && apt-get install -y tesseract-ocr
COPY requirements.txt .
RUN pip install -r requirements.txt
```

## Testing Your Setup

### Quick Test
```bash
# Test text PDF
python -c "
from app.services.document_service import extract_text_from_file
with open('your_pdf.pdf', 'rb') as f:
    text = extract_text_from_file(f, 'your_pdf.pdf')
    print(f'Extracted: {len(text)} characters')
"
```

### Full Test Suite
```bash
python test_pdf_processing.py
```

---

**Your bot can now handle ANY PDF - text, scanned, or mixed!** 🎉

Need help? Check logs in the terminal running your FastAPI server.
