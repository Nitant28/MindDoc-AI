"""
blockchain_audit_manager.py
Blockchain audit trail: Immutable, transparent compliance records.
"""

from typing import Dict, Any, List
import hashlib

class BlockchainAuditManager:
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self.last_hash = ""

    def add_record(self, record: Dict[str, Any]):
        record_hash = hashlib.sha256(str(record).encode() + self.last_hash.encode()).hexdigest()
        self.chain.append({"record": record, "hash": record_hash})
        self.last_hash = record_hash
        print(f"Blockchain record added: {record_hash}")

    def verify_chain(self) -> bool:
        prev_hash = ""
        for block in self.chain:
            expected_hash = hashlib.sha256(str(block["record"]).encode() + prev_hash.encode()).hexdigest()
            if block["hash"] != expected_hash:
                return False
            prev_hash = block["hash"]
        return True

blockchain_audit_manager = BlockchainAuditManager()

# Example usage:
# blockchain_audit_manager.add_record({"compliance": "filed"})
# print(blockchain_audit_manager.verify_chain())
