"""
Reservation Service.
Manages book reservations for members, fulfillment workflows, and duplicate protection.
"""

import datetime
from typing import Optional, Tuple
from database import DatabaseManager
from models.reservation import Reservation
from utils.logger import log_event


class ReservationService:
    """
    Service for book hold reservations.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def _generate_reservation_id(self) -> str:
        today_str = datetime.date.today().strftime("%Y%m%d")
        prefix = f"RES{today_str}"
        row = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM reservations WHERE reservation_id LIKE ?",
            (f"{prefix}%",)
        )
        count = row["count"] + 1
        return f"{prefix}{count:04d}"

    def _reservation_query_base(self) -> str:
        return """
            SELECT 
                r.*,
                m.full_name as member_name,
                m.member_id as member_code,
                b.title as book_title,
                b.isbn as book_isbn,
                b.available_quantity as available_quantity
            FROM reservations r
            JOIN members m ON r.member_id = m.id
            JOIN books b ON r.book_id = b.id
        """

    def create_reservation(self, member_id_num: int, book_identifier: str) -> Tuple[bool, str, Optional[Reservation]]:
        """
        Reserve a book for a member.
        book_identifier: ISBN or book ID
        """
        # 1. Verify Member
        member = self.db.fetch_one("SELECT * FROM members WHERE id = ?", (member_id_num,))
        if not member:
            return False, "Member record not found.", None
        if member["status"] != "Active":
            return False, "Your account is BLOCKED. You cannot create reservations.", None

        # 2. Verify Book
        clean_isbn = book_identifier.strip().replace("-", "").replace(" ", "")
        book = self.db.fetch_one(
            "SELECT * FROM books WHERE isbn = ? OR id = ?",
            (clean_isbn, book_identifier)
        )
        if not book:
            return False, f"Book '{book_identifier}' not found in the catalog.", None

        book_id = book["id"]

        # 3. Check for existing pending reservation
        existing = self.db.fetch_one(
            "SELECT id FROM reservations WHERE member_id = ? AND book_id = ? AND status = 'Pending'",
            (member_id_num, book_id)
        )
        if existing:
            return False, f"You already have a PENDING reservation for '{book['title']}'.", None

        # 4. Check if member already currently borrowed the book
        active_borrowing = self.db.fetch_one(
            "SELECT id FROM borrowings WHERE member_id = ? AND book_id = ? AND status = 'Issued'",
            (member_id_num, book_id)
        )
        if active_borrowing:
            return False, f"You currently have an active borrowed copy of '{book['title']}'.", None

        # 5. Insert Reservation
        res_code = self._generate_reservation_id()
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        try:
            self.db.execute_update(
                """
                INSERT INTO reservations (reservation_id, member_id, book_id, reservation_date, status)
                VALUES (?, ?, ?, ?, 'Pending')
                """,
                (res_code, member_id_num, book_id, today_str)
            )
            log_event("INFO", f"Reservation created: {res_code} by member ID {member_id_num} for book ID {book_id}")

            row = self.db.fetch_one(
                f"{self._reservation_query_base()} WHERE r.reservation_id = ?",
                (res_code,)
            )
            return True, f"Reservation created successfully! Reservation ID: {res_code}", Reservation.from_row(row)
        except Exception as e:
            log_event("ERROR", f"Error creating reservation: {e}")
            return False, f"Failed to create reservation: {e}", None

    def cancel_reservation(self, reservation_code: str, member_id_num: Optional[int] = None) -> Tuple[bool, str]:
        """
        Cancel a pending reservation.
        """
        row = self.db.fetch_one(
            "SELECT * FROM reservations WHERE reservation_id = ? COLLATE NOCASE",
            (reservation_code.strip(),)
        )
        if not row:
            return False, f"Reservation '{reservation_code}' not found."

        if member_id_num and row["member_id"] != member_id_num:
            return False, "You can only cancel your own reservations."

        if row["status"] != "Pending":
            return False, f"Cannot cancel reservation because its status is already '{row['status']}'."

        try:
            self.db.execute_update(
                "UPDATE reservations SET status = 'Cancelled' WHERE id = ?",
                (row["id"],)
            )
            log_event("INFO", f"Reservation {reservation_code} cancelled.")
            return True, f"Reservation '{reservation_code}' has been cancelled."
        except Exception as e:
            log_event("ERROR", f"Error cancelling reservation: {e}")
            return False, f"Failed to cancel reservation: {e}"

    def fulfill_reservation(self, reservation_code: str) -> Tuple[bool, str]:
        """
        Admin action: Mark a pending reservation as fulfilled.
        """
        row = self.db.fetch_one(
            f"{self._reservation_query_base()} WHERE r.reservation_id = ? COLLATE NOCASE",
            (reservation_code.strip(),)
        )
        if not row:
            return False, f"Reservation '{reservation_code}' not found."

        if row["status"] != "Pending":
            return False, f"Cannot fulfill reservation with status '{row['status']}'."

        try:
            self.db.execute_update(
                "UPDATE reservations SET status = 'Fulfilled' WHERE id = ?",
                (row["id"],)
            )
            log_event("INFO", f"Reservation {reservation_code} fulfilled.")
            return True, f"Reservation '{reservation_code}' for member '{row['member_name']}' marked as FULFILLED."
        except Exception as e:
            log_event("ERROR", f"Error fulfilling reservation: {e}")
            return False, f"Failed to fulfill reservation: {e}"

    def get_pending_reservations(self) -> list[Reservation]:
        rows = self.db.fetch_all(
            f"{self._reservation_query_base()} WHERE r.status = 'Pending' ORDER BY r.reservation_date ASC"
        )
        return [Reservation.from_row(r) for r in rows]

    def get_all_reservations(self, status: Optional[str] = None) -> list[Reservation]:
        if status and status.upper() != "ALL":
            sql = f"{self._reservation_query_base()} WHERE r.status = ? ORDER BY r.id DESC"
            rows = self.db.fetch_all(sql, (status,))
        else:
            sql = f"{self._reservation_query_base()} ORDER BY r.id DESC"
            rows = self.db.fetch_all(sql)
        return [Reservation.from_row(r) for r in rows]

    def get_member_reservations(self, member_id_num: int) -> list[Reservation]:
        rows = self.db.fetch_all(
            f"{self._reservation_query_base()} WHERE r.member_id = ? ORDER BY r.id DESC",
            (member_id_num,)
        )
        return [Reservation.from_row(r) for r in rows]
