"""
Author Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Author:
    id: Optional[int]
    name: str
    biography: Optional[str] = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Author":
        return cls(
            id=row["id"],
            name=row["name"],
            biography=row["biography"] if "biography" in row.keys() else "",
            created_at=row["created_at"] if "created_at" in row.keys() else None
        )

    def to_dict(self) -> dict:
        return {
            "ID": self.id,
            "Name": self.name,
            "Biography": self.biography or "N/A",
            "Created At": self.created_at
        }
