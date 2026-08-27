"""
Book Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Book:
    id: Optional[int]
    isbn: str
    title: str
    author_id: int
    category_id: int
    publisher_id: int
    publication_year: int
    edition: Optional[str]
    quantity: int
    available_quantity: int
    shelf_location: Optional[str]
    status: str = "Available"
    created_at: Optional[str] = None
    # Joined fields for display
    author_name: Optional[str] = None
    category_name: Optional[str] = None
    publisher_name: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Book":
        keys = row.keys()
        return cls(
            id=row["id"],
            isbn=row["isbn"],
            title=row["title"],
            author_id=row["author_id"],
            category_id=row["category_id"],
            publisher_id=row["publisher_id"],
            publication_year=row["publication_year"],
            edition=row["edition"] if "edition" in keys else "",
            quantity=row["quantity"],
            available_quantity=row["available_quantity"],
            shelf_location=row["shelf_location"] if "shelf_location" in keys else "",
            status=row["status"],
            created_at=row["created_at"] if "created_at" in keys else None,
            author_name=row["author_name"] if "author_name" in keys else None,
            category_name=row["category_name"] if "category_name" in keys else None,
            publisher_name=row["publisher_name"] if "publisher_name" in keys else None
        )

    def to_dict(self) -> dict:
        return {
            "ID": self.id,
            "ISBN": self.isbn,
            "Title": self.title,
            "Author": self.author_name or f"ID: {self.author_id}",
            "Category": self.category_name or f"ID: {self.category_id}",
            "Publisher": self.publisher_name or f"ID: {self.publisher_id}",
            "Year": self.publication_year,
            "Edition": self.edition or "1st",
            "Quantity": self.quantity,
            "Available": self.available_quantity,
            "Shelf": self.shelf_location or "N/A",
            "Status": self.status
        }
