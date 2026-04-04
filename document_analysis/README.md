# Document Analysis API

## Live API
The main endpoint is:
POST /analyze-document

This endpoint accepts multipart file uploads and returns AI-powered document analysis in JSON format.

## Authentication
All requests require an API key in the Authorization header:
```
Authorization: Bearer <API_KEY>
```

## Example curl
```bash
curl -X POST "LIVE_URL/analyze-document" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@sample.pdf"
```

## Response Format
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

## AI Tools Used
- Groq (LLaMA/Mixtral models)
- ChatGPT (for prompt engineering)
- Copilot (for code assistance)

## Deployment Steps

1. Push this project to GitHub
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `API_KEY`: Your chosen API key
   - `GROQ_API_KEY`: Your Groq API key
7. Deploy and get your live URL

## Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Testing
```bash
python test_api.py
```