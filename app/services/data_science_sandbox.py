"""
data_science_sandbox.py
Data science sandbox: Analyze compliance data with built-in Jupyter/Colab integration.
"""

import pandas as pd
from typing import List, Dict, Any

class DataScienceSandbox:
    def __init__(self):
        self.data: List[Dict[str, Any]] = []

    def add_data(self, record: Dict[str, Any]):
        self.data.append(record)

    def get_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.data)

    def export_to_csv(self, path: str = "sandbox_data.csv") -> str:
        df = self.get_dataframe()
        df.to_csv(path, index=False)
        return path

data_science_sandbox = DataScienceSandbox()

# Example usage:
# data_science_sandbox.add_data({"status": "filed", "risk": 0.2})
# print(data_science_sandbox.get_dataframe())
# print(data_science_sandbox.export_to_csv())
