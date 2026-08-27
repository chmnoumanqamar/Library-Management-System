"""
Borrowing Model.
"""

from dataclasses import dataclass
import datetime
from typing import Optional
import sqlite3


@dataclass
class Borrowing:
    id: Optional[int]
    borrowing_id: str
    member_id: int
    book_id: int
    issue_date: str
    due_date: str
    return_date: Optional[str] = None
    renewal_count: int = 0
    status: str = "Issued"  # 'Issued', 'Returned', 'Overdue'
    created_at: Optional[str] = None
    # Joined fields for presentation
    member_name: Optional[str] = None
    member_code: Optional[str] = None
    book_title: Optional[str] = None
    book_isbn: Optional[str] = None

    def calculate_overdue_days(self, as_of_date: Optional[datetime.date] = None) -> int:
        """Calculate how many days overdue this borrowing is."""
        if self.status == "Returned" and self.return_date:
            try:
                ret_dt = datetime.datetime.strptime(self.return_date, "%Y-%m-%d").date()
                due_dt = datetime.datetime.strptime(self.due_date, "%Y-%m-%d").date()
                return max(0, (ret_dt - due_dt).days)
            except ValueError:
                return 0

        target_date = as_of_date or datetime.date.today()
        try:
            due_dt = datetime.datetime.strptime(self.due_date, "%Y-%m-%d").date()
            return max(0, (target_date - due_dt).days)
        except ValueError:
            return 0

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Borrowing":
        keys = row.keys()
        return cls(
            id=row["id"],
            borrowing_id=row["borrowing_id"],
            member_id=row["member_id"],
            book_id=row["book_id"],
            issue_date=row["issue_date"],
            due_date=row["due_date"],
            return_date=row["return_date"] if "return_date" in keys else None,
            renewal_count=row["renewal_count"] if "renewal_count" in keys else 0,
            status=row["status"],
            created_at=row["created_at"] if "created_at" in keys else None,
            member_name=row["member_name"] if "member_name" in keys else None,
            member_code=row["member_code"] if "member_code" in keys else None,
            book_title=row["book_title"] if "book_title" in keys else None,
            book_isbn=row["book_isbn"] if "book_isbn" in keys else None
        )

    def to_dict(self) -> dict:
        return {
            "Borrowing ID": self.borrowing_id,
            "Member": f"{self.member_name} ({self.member_code})" if self.member_name else f"ID: {self.member_id}",
            "Book": self.book_title or f"ID: {self.book_id}",
            "ISBN": self.book_isbn or "N/A",
            "Issue Date": self.issue_date,
            "Due Date": self.due_date,
            "Return Date": self.return_date or "-",
            "Renewals": self.renewal_count,
            "Status": self.status
        }
