"""
notebook_manager.py
Jupyter/Colab notebook manager for launching, exporting, and syncing compliance analysis notebooks.
"""

import os
import nbformat
from nbformat.v4 import new_notebook, new_code_cell

class NotebookManager:
    def __init__(self, notebook_dir: str = "notebooks"):
        self.notebook_dir = notebook_dir
        os.makedirs(self.notebook_dir, exist_ok=True)

    def create_notebook(self, name: str, cells: list = None) -> str:
        nb = new_notebook()
        if cells:
            nb.cells = [new_code_cell(cell) for cell in cells]
        path = os.path.join(self.notebook_dir, f"{name}.ipynb")
        with open(path, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)
        return path

    def list_notebooks(self) -> list:
        return [f for f in os.listdir(self.notebook_dir) if f.endswith(".ipynb")]

    def export_notebook(self, name: str, export_path: str) -> str:
        src = os.path.join(self.notebook_dir, f"{name}.ipynb")
        if os.path.exists(src):
            os.rename(src, export_path)
            return export_path
        return ""

notebook_manager = NotebookManager()

# Example usage:
# notebook_manager.create_notebook("compliance_analysis", ["import pandas as pd", "print('Hello, Compliance!')"])
# print(notebook_manager.list_notebooks())
