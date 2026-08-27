"""
Member Management Service.
Handles member retrieval, searching, profile updates, blocking/unblocking, and deletion safety.
"""

from decimal import Decimal
from typing import Optional, Tuple
from database import DatabaseManager
from models.member import Member
from utils.logger import log_event
from utils.validators import validate_email, validate_name, validate_phone


class MemberService:
    """
    Service for member records, account status, and profile management.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def get_all_members(self) -> list[Member]:
        rows = self.db.fetch_all("SELECT * FROM members ORDER BY id DESC")
        return [Member.from_row(r) for r in rows]

    def get_member_by_id(self, member_db_id: int) -> Optional[Member]:
        row = self.db.fetch_one("SELECT * FROM members WHERE id = ?", (member_db_id,))
        return Member.from_row(row) if row else None

    def get_member_by_code(self, member_id_code: str) -> Optional[Member]:
        code = member_id_code.strip()
        row = self.db.fetch_one("SELECT * FROM members WHERE member_id = ? COLLATE NOCASE", (code,))
        return Member.from_row(row) if row else None

    def get_member_by_username(self, username: str) -> Optional[Member]:
        u = username.strip()
        row = self.db.fetch_one("SELECT * FROM members WHERE username = ? COLLATE NOCASE", (u,))
        return Member.from_row(row) if row else None

    def search_members(self, query: str) -> list[Member]:
        term = f"%{query.strip()}%"
        sql = """
            SELECT * FROM members
            WHERE member_id LIKE ?
               OR full_name LIKE ?
               OR cnic LIKE ?
               OR phone LIKE ?
               OR username LIKE ?
               OR email LIKE ?
            ORDER BY full_name ASC
        """
        rows = self.db.fetch_all(sql, (term, term, term, term, term, term))
        return [Member.from_row(r) for r in rows]

    def update_profile(
        self,
        member_id_num: int,
        full_name: str,
        phone: str,
        email: str,
        address: str
    ) -> Tuple[bool, str]:
        valid_name, err_name = validate_name(full_name)
        if not valid_name:
            return False, err_name

        valid_phone, err_phone = validate_phone(phone)
        if not valid_phone:
            return False, err_phone

        valid_email, err_email = validate_email(email)
        if not valid_email:
            return False, err_email

        if not address or not address.strip():
            return False, "Address cannot be empty."

        try:
            self.db.execute_update(
                """
                UPDATE members
                SET full_name = ?, phone = ?, email = ?, address = ?
                WHERE id = ?
                """,
                (full_name.strip(), phone.strip(), email.strip().lower(), address.strip(), member_id_num)
            )
            log_event("INFO", f"Member ID {member_id_num} profile updated.")
            return True, "Profile updated successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating member profile: {e}")
            return False, f"Failed to update profile: {e}"

    def block_member(self, member_id_num: int) -> Tuple[bool, str]:
        member = self.get_member_by_id(member_id_num)
        if not member:
            return False, "Member not found."
        if member.status == "Blocked":
            return False, f"Member '{member.full_name}' is already blocked."

        try:
            self.db.execute_update("UPDATE members SET status = 'Blocked' WHERE id = ?", (member_id_num,))
            log_event("WARNING", f"Member {member.member_id} ({member.full_name}) was BLOCKED.")
            return True, f"Member '{member.full_name}' has been blocked."
        except Exception as e:
            log_event("ERROR", f"Error blocking member: {e}")
            return False, f"Failed to block member: {e}"

    def unblock_member(self, member_id_num: int) -> Tuple[bool, str]:
        member = self.get_member_by_id(member_id_num)
        if not member:
            return False, "Member not found."
        if member.status == "Active":
            return False, f"Member '{member.full_name}' is already active."

        try:
            self.db.execute_update("UPDATE members SET status = 'Active' WHERE id = ?", (member_id_num,))
            log_event("INFO", f"Member {member.member_id} ({member.full_name}) was UNBLOCKED.")
            return True, f"Member '{member.full_name}' has been unblocked and is now active."
        except Exception as e:
            log_event("ERROR", f"Error unblocking member: {e}")
            return False, f"Failed to unblock member: {e}"

    def delete_member(self, member_id_num: int) -> Tuple[bool, str]:
        member = self.get_member_by_id(member_id_num)
        if not member:
            return False, "Member not found."

        # Check active borrowings
        active_b = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE member_id = ? AND status = 'Issued'",
            (member_id_num,)
        )["count"]
        if active_b > 0:
            return False, f"Cannot delete member. Member has {active_b} active borrowed book(s)."

        # Check unpaid fines
        unpaid_f = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM fines WHERE member_id = ? AND status = 'Unpaid'",
            (member_id_num,)
        )["count"]
        if unpaid_f > 0:
            return False, f"Cannot delete member. Member has {unpaid_f} unpaid fine record(s)."

        try:
            with self.db.transaction() as conn:
                # Cancel pending reservations
                conn.execute(
                    "UPDATE reservations SET status = 'Cancelled' WHERE member_id = ? AND status = 'Pending'",
                    (member_id_num,)
                )
                conn.execute("DELETE FROM members WHERE id = ?", (member_id_num,))
            
            log_event("INFO", f"Member {member.member_id} ({member.full_name}) deleted.")
            return True, f"Member '{member.full_name}' deleted successfully."
        except Exception as e:
            log_event("ERROR", f"Error deleting member ID {member_id_num}: {e}")
            return False, f"Failed to delete member: {e}"

    def get_member_stats(self, member_id_num: int) -> dict:
        """
        Calculate live statistics for the member dashboard.
        """
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # Active borrowed books
        active_borrowed = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE member_id = ? AND status = 'Issued'",
            (member_id_num,)
        )["count"]

        # Overdue books (issued and due_date < today)
        overdue_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE member_id = ? AND status = 'Issued' AND due_date < ?",
            (member_id_num, today)
        )["count"]

        # Pending reservations
        pending_reservations = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM reservations WHERE member_id = ? AND status = 'Pending'",
            (member_id_num,)
        )["count"]

        # Unpaid fines sum
        fine_row = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount), 0) as total FROM fines WHERE member_id = ? AND status = 'Unpaid'",
            (member_id_num,)
        )
        unpaid_fine_amount = Decimal(str(fine_row["total"]))

        return {
            "borrowed_books": active_borrowed,
            "overdue_books": overdue_count,
            "pending_reservations": pending_reservations,
            "unpaid_fine": unpaid_fine_amount
        }
