"""
Fine Management Service.
Handles fine retrieval, status filtering, payment recording, and monetary statistics.
"""

import datetime
from decimal import Decimal
from typing import Optional, Tuple
from database import DatabaseManager
from models.fine import Fine
from utils.logger import log_event


class FineService:
    """
    Service for managing library fines and payments.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def _fine_query_base(self) -> str:
        return """
            SELECT 
                f.*,
                m.full_name as member_name,
                m.member_id as member_code,
                bw.borrowing_id as borrowing_code,
                b.title as book_title
            FROM fines f
            JOIN members m ON f.member_id = m.id
            LEFT JOIN borrowings bw ON f.borrowing_id = bw.id
            LEFT JOIN books b ON bw.book_id = b.id
        """

    def get_all_fines(self, status: Optional[str] = None) -> list[Fine]:
        """Fetch all fines, optionally filtered by status ('Unpaid' or 'Paid')."""
        if status and status.upper() != "ALL":
            sql = f"{self._fine_query_base()} WHERE f.status = ? ORDER BY f.id DESC"
            rows = self.db.fetch_all(sql, (status,))
        else:
            sql = f"{self._fine_query_base()} ORDER BY f.id DESC"
            rows = self.db.fetch_all(sql)
        return [Fine.from_row(r) for r in rows]

    def get_fine_by_id(self, fine_id: int) -> Optional[Fine]:
        sql = f"{self._fine_query_base()} WHERE f.id = ?"
        row = self.db.fetch_one(sql, (fine_id,))
        return Fine.from_row(row) if row else None

    def get_member_fines(self, member_id_num: int) -> list[Fine]:
        """Fetch fines for a specific member."""
        sql = f"{self._fine_query_base()} WHERE f.member_id = ? ORDER BY f.id DESC"
        rows = self.db.fetch_all(sql, (member_id_num,))
        return [Fine.from_row(r) for r in rows]

    def mark_fine_as_paid(self, fine_id: int) -> Tuple[bool, str]:
        """Mark an unpaid fine as paid."""
        fine = self.get_fine_by_id(fine_id)
        if not fine:
            return False, f"Fine record #{fine_id} not found."

        if fine.status == "Paid":
            return False, f"Fine #{fine_id} is already marked as PAID on {fine.paid_at}."

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.db.execute_update(
                "UPDATE fines SET status = 'Paid', paid_at = ? WHERE id = ?",
                (now_str, fine_id)
            )
            log_event("INFO", f"Fine #{fine_id} (Rs. {fine.amount}) marked as PAID for member {fine.member_name}")
            return True, f"Fine #{fine_id} of Rs. {fine.amount:,.2f} marked as PAID successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating fine status: {e}")
            return False, f"Failed to record fine payment: {e}"

    def get_fine_statistics(self) -> dict:
        """
        Aggregate fine statistics for reports and dashboards.
        """
        total_row = self.db.fetch_one("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total FROM fines")
        paid_row = self.db.fetch_one("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total FROM fines WHERE status = 'Paid'")
        unpaid_row = self.db.fetch_one("SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total FROM fines WHERE status = 'Unpaid'")

        return {
            "total_fines_count": total_row["count"],
            "total_fines_amount": Decimal(str(total_row["total"])),
            "paid_fines_count": paid_row["count"],
            "paid_fines_amount": Decimal(str(paid_row["total"])),
            "unpaid_fines_count": unpaid_row["count"],
            "unpaid_fines_amount": Decimal(str(unpaid_row["total"]))
        }
