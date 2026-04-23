"""
plugin_marketplace.py
Plugin marketplace: Users can build and share custom modules for new laws, integrations, etc.
"""

from typing import Dict, List, Any

class PluginMarketplace:
    def __init__(self):
        self.plugins: List[Dict[str, Any]] = []

    def add_plugin(self, name: str, description: str, code: str):
        self.plugins.append({"name": name, "description": description, "code": code})

    def get_plugins(self) -> List[Dict[str, Any]]:
        return self.plugins

plugin_marketplace = PluginMarketplace()

# Example usage:
# plugin_marketplace.add_plugin("GST Calculator", "Calculates GST for invoices", "def calc_gst(...): ...")
# print(plugin_marketplace.get_plugins())
