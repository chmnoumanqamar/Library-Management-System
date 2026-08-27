"""
Reservation Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Reservation:
    id: Optional[int]
    reservation_id: str
    member_id: int
    book_id: int
    reservation_date: str
    status: str = "Pending"  # 'Pending', 'Fulfilled', 'Cancelled'
    created_at: Optional[str] = None
    # Joined fields
    member_name: Optional[str] = None
    member_code: Optional[str] = None
    book_title: Optional[str] = None
    book_isbn: Optional[str] = None
    available_quantity: Optional[int] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Reservation":
        keys = row.keys()
        return cls(
            id=row["id"],
            reservation_id=row["reservation_id"],
            member_id=row["member_id"],
            book_id=row["book_id"],
            reservation_date=row["reservation_date"],
            status=row["status"],
            created_at=row["created_at"] if "created_at" in keys else None,
            member_name=row["member_name"] if "member_name" in keys else None,
            member_code=row["member_code"] if "member_code" in keys else None,
            book_title=row["book_title"] if "book_title" in keys else None,
            book_isbn=row["book_isbn"] if "book_isbn" in keys else None,
            available_quantity=row["available_quantity"] if "available_quantity" in keys else None
        )

    def to_dict(self) -> dict:
        return {
            "Reservation ID": self.reservation_id,
            "Member": f"{self.member_name} ({self.member_code})" if self.member_name else f"ID: {self.member_id}",
            "Book": self.book_title or f"ID: {self.book_id}",
            "ISBN": self.book_isbn or "N/A",
            "Reserved On": self.reservation_date,
            "Status": self.status,
            "Available Stock": self.available_quantity if self.available_quantity is not None else "N/A"
        }
