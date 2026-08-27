"""
Admin Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Admin:
    id: Optional[int]
    username: str
    password_hash: str
    salt: str
    full_name: str
    email: str
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Admin":
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            full_name=row["full_name"],
            email=row["email"],
            created_at=row["created_at"] if "created_at" in row.keys() else None
        )

    def to_dict(self) -> dict:
        return {
            "ID": self.id,
            "Username": self.username,
            "Full Name": self.full_name,
            "Email": self.email,
            "Created At": self.created_at
        }
