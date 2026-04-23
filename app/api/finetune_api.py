from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.models import get_db
from app.services.document_service import parse_document, chunk_document
from app.services.ollama_client import generate_with_ollama
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) )
# NOTE: ollama_contract_finetune module was removed during cleanup - these functions are not available
# from ollama_contract_finetune import analyze_contract, highlight_clauses
import shutil

router = APIRouter()
UPLOAD_DIR = os.path.join(os.getcwd(), "data", "finetune_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/finetune/upload")
def finetune_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="Fine-tuning feature is not available in this version")
