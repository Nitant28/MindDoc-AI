"""
notebook_api.py
API endpoints for launching, exporting, and syncing Jupyter/Colab notebooks for compliance analysis.
"""

from fastapi import APIRouter, HTTPException
from app.services.notebook_manager import notebook_manager

router = APIRouter()

@router.post("/notebook/create")
def create_notebook(name: str, cells: list = None):
    path = notebook_manager.create_notebook(name, cells)
    return {"notebook_path": path}

@router.get("/notebook/list")
def list_notebooks():
    notebooks = notebook_manager.list_notebooks()
    return {"notebooks": notebooks}

@router.post("/notebook/export")
def export_notebook(name: str, export_path: str):
    result = notebook_manager.export_notebook(name, export_path)
    if not result:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"exported_path": result}
