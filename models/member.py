"""
Member Model.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass
class Member:
    id: Optional[int]
    member_id: str
    full_name: str
    cnic: str
    phone: str
    email: str
    address: str
    username: str
    password_hash: str
    salt: str
    status: str = "Active"  # 'Active' or 'Blocked'
    created_at: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.status == "Active"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Member":
        keys = row.keys()
        return cls(
            id=row["id"],
            member_id=row["member_id"],
            full_name=row["full_name"],
            cnic=row["cnic"],
            phone=row["phone"],
            email=row["email"],
            address=row["address"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            status=row["status"],
            created_at=row["created_at"] if "created_at" in keys else None
        )

    def to_dict(self) -> dict:
        return {
            "ID": self.id,
            "Member ID": self.member_id,
            "Full Name": self.full_name,
            "CNIC": self.cnic,
            "Phone": self.phone,
            "Email": self.email,
            "Address": self.address,
            "Username": self.username,
            "Status": self.status,
            "Joined": self.created_at
        }
