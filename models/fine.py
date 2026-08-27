"""
Fine Model.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import sqlite3
from config import CURRENCY_SYMBOL


@dataclass
class Fine:
    id: Optional[int]
    borrowing_id: Optional[int]
    member_id: int
    amount: Decimal
    reason: str
    status: str = "Unpaid"  # 'Unpaid', 'Paid'
    created_at: Optional[str] = None
    paid_at: Optional[str] = None
    # Joined fields
    member_name: Optional[str] = None
    member_code: Optional[str] = None
    borrowing_code: Optional[str] = None
    book_title: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Fine":
        keys = row.keys()
        return cls(
            id=row["id"],
            borrowing_id=row["borrowing_id"] if "borrowing_id" in keys else None,
            member_id=row["member_id"],
            amount=Decimal(str(row["amount"])),
            reason=row["reason"],
            status=row["status"],
            created_at=row["created_at"] if "created_at" in keys else None,
            paid_at=row["paid_at"] if "paid_at" in keys else None,
            member_name=row["member_name"] if "member_name" in keys else None,
            member_code=row["member_code"] if "member_code" in keys else None,
            borrowing_code=row["borrowing_code"] if "borrowing_code" in keys else None,
            book_title=row["book_title"] if "book_title" in keys else None
        )

    def to_dict(self) -> dict:
        return {
            "Fine ID": self.id,
            "Borrowing ID": self.borrowing_code or "-",
            "Member": f"{self.member_name} ({self.member_code})" if self.member_name else f"ID: {self.member_id}",
            "Book": self.book_title or "-",
            "Amount": f"{CURRENCY_SYMBOL} {self.amount:,.2f}",
            "Reason": self.reason,
            "Status": self.status,
            "Date": self.created_at or "-",
            "Paid Date": self.paid_at or "-"
        }
