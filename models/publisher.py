"""
Publisher Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Publisher:
    id: Optional[int]
    name: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Publisher":
        return cls(
            id=row["id"],
            name=row["name"],
            contact=row["contact"] if "contact" in row.keys() else "",
            email=row["email"] if "email" in row.keys() else "",
            address=row["address"] if "address" in row.keys() else "",
            created_at=row["created_at"] if "created_at" in row.keys() else None
        )

    def to_dict(self) -> dict:
        return {
            "ID": self.id,
            "Name": self.name,
            "Contact": self.contact or "N/A",
            "Email": self.email or "N/A",
            "Address": self.address or "N/A",
            "Created At": self.created_at
        }
