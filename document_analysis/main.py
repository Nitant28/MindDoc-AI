from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv
from services.document_processor import DocumentProcessor
from services.ai_analyzer import AIAnalyzer
from services.fallback_analyzer import FallbackAnalyzer
from utils.text_cleaner import clean_text
from utils.chunker import chunk_text
from models.response_models import AnalysisResponse
import time
import asyncio

load_dotenv()

app = FastAPI(title="Document Analysis API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Services
doc_processor = DocumentProcessor()
ai_analyzer = AIAnalyzer()
fallback_analyzer = FallbackAnalyzer()

API_KEY = os.getenv("API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def verify_api_key(request: Request):
    authorization = request.headers.get("authorization")
    if not authorization:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Missing API key"}
        )
    if not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Missing API key"}
        )
    token = authorization[7:]
    if token != API_KEY:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Invalid API key"}
        )
    return None

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-document")
async def analyze_document(
    request: Request,
    file: UploadFile = File(...)
):
    logger.info("Request received for /analyze-document")
    
    if not API_KEY or not GROQ_API_KEY:
        logger.error("Missing API_KEY or GROQ_API_KEY environment variable")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Server configuration missing API_KEY or GROQ_API_KEY"}
        )

    # Auth check
    auth_error = await verify_api_key(request)
    if auth_error:
        return auth_error
    
    # Validate file
    if not file:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No file provided"}
        )
    
    allowed_types = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                     'image/png', 'image/jpeg', 'image/bmp', 'image/tiff']
    if file.content_type not in allowed_types:
        logger.warning(f"Unsupported file type: {file.content_type}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Unsupported file type"}
        )
    
    logger.info(f"Processing file: {file.filename}, type: {file.content_type}")
    
    try:
        start_time = time.time()
        
        # Read file
        file_bytes = await file.read()
        logger.info("File read successfully")
        
        # Extract text
        raw_text = doc_processor.extract_text(file_bytes, file.filename)
        if not raw_text:
            logger.warning("Text extraction failed, using fallback")
            raw_text = "Document text extraction failed. This is a placeholder for analysis."
        
        logger.info("Text extracted, length: %d", len(raw_text))
        
        # Clean text
        cleaned_text = clean_text(raw_text)
        
        # Chunk if large
        chunks = chunk_text(cleaned_text)
        text_to_analyze = chunks[0] if chunks else cleaned_text
        logger.info("Text cleaned and chunked")
        
        # AI Analysis
        analysis = await asyncio.get_event_loop().run_in_executor(None, ai_analyzer.analyze, text_to_analyze)
        if analysis is None:
            logger.warning("AI analysis failed, using fallback")
            analysis = await asyncio.get_event_loop().run_in_executor(None, fallback_analyzer.analyze, text_to_analyze)
        
        logger.info("Analysis completed")
        
        # Ensure response format
        response = {
            "status": "success",
            "summary": analysis.get("summary", ""),
            "key_entities": analysis.get("key_entities", {"names": [], "dates": [], "amounts": []}),
            "important_clauses": analysis.get("important_clauses", []),
            "risk_flags": analysis.get("risk_flags", []),
            "confidence_score": analysis.get("confidence_score", 0.0)
        }
        
        elapsed = time.time() - start_time
        logger.info(f"Analysis completed in {elapsed:.2f}s")
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Something went wrong"}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)