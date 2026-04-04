# Document Analysis API

## Live URL
Live URL: not deployed yet. Update this after deploying on Render.

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/Nitant28/MindDoc-AI.git
   cd "MindDoc AI - RAG Multi-Tenant"/document_analysis
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment template:
   ```bash
   cp .env.example .env
   ```
4. Set environment values in `.env` or in Render:
   - `API_KEY=nitant123`
   - `GROQ_API_KEY=<your_actual_groq_api_key>`

3. Copy environment template:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and set:
   - `API_KEY=nitant123`
   - `GROQ_API_KEY=<your_actual_key>`
5. Run locally:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Architecture Overview
This project is a modular FastAPI application for document analysis.
- `main.py`: API routes, auth validation, file validation, pipeline orchestration.
- `services/document_processor.py`: Extracts text from PDF, DOCX, and image files.
- `services/ai_analyzer.py`: Sends document text to the Groq API for structured analysis.
- `services/fallback_analyzer.py`: Uses regex and keyword analysis when Groq is unavailable.
- `utils/`: Text cleaning and chunking helper utilities.
- `models/response_models.py`: Defines the JSON response schema.

## Tech Stack
- Python 3.11+
- FastAPI
- Uvicorn
- PyMuPDF
- python-docx
- EasyOCR
- Requests
- python-dotenv
- Groq API

## AI Tools Used
- Groq API for document analysis and extraction
- ChatGPT for prompt design and documentation guidance
- GitHub Copilot for coding assistance

## Known Limitations
- Requires a valid `GROQ_API_KEY` for full AI analysis.
- If Groq is unavailable, the app falls back to rule-based extraction.
- EasyOCR runs on CPU in this environment and can be slow for large images.
- Document analysis is not yet live on a public URL from this execution environment.

## API Endpoints
- `GET /health`
  - Response: `{"status": "ok"}`
- `POST /analyze-document`
  - Requires `Authorization: Bearer <API_KEY>`
  - Accepts PDF, DOCX, PNG, JPG, JPEG, BMP, TIFF

## Example curl
```bash
curl -X POST "LIVE_URL/analyze-document" \
  -H "Authorization: Bearer nitant123" \
  -F "file=@sample.pdf"
```

## Expected Response Format
```json
{
  "status": "success",
  "summary": "Document summary here",
  "key_entities": {
    "names": ["John Doe"],
    "dates": ["2024-01-01"],
    "amounts": ["$1000"]
  },
  "important_clauses": ["Clause 1", "Clause 2"],
  "risk_flags": ["Risk 1", "Risk 2"],
  "confidence_score": 0.85
}
```

## Render Deployment
This project includes `render.yaml` so Render can automatically configure the service when connected.

1. Push the `document_analysis` project to GitHub.
2. Create a new Web Service on Render.
3. Connect the GitHub repository.
4. If Render does not auto-detect the service, set the root directory to `document_analysis`.
5. Render will use `render.yaml` to configure build/start commands.
6. Add environment variables in the Render dashboard:
   - `API_KEY=nitant123`
   - `GROQ_API_KEY=<your_actual_key>`
7. Deploy and wait for Render to finish.

## Testing
```bash
python test_api.py
```
