"""
notebook_sandbox.md
# Data Science Sandbox & Notebook Integration

This module enables users to:
- Analyze compliance/tax data in a Jupyter/Colab-style sandbox
- Launch, export, and sync notebooks for custom analysis
- Use built-in Pandas support for data exploration
- Export results to CSV for further processing

## API Endpoints
- `/api/notebook/create` — Create a new notebook
- `/api/notebook/list` — List available notebooks
- `/api/notebook/export` — Export a notebook to a custom path

## Usage Example
1. POST to `/api/notebook/create` with notebook name and code cells
2. GET `/api/notebook/list` to view available notebooks
3. POST to `/api/notebook/export` to export a notebook

## Data Science Sandbox
- Add compliance/tax records via Python API
- Analyze with Pandas
- Export to CSV for reporting

## Next Steps
- Integrate with frontend for one-click notebook launch
- Enable Colab sync for mobile users
- Add sample notebooks for compliance/tax analysis
