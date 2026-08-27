"""
Borrowing & Circulation Service.
Manages book issuance, returns, renewals, overdue detection, and transaction safety.
"""

import datetime
from decimal import Decimal
from typing import Optional, Tuple
from config import (
    DEFAULT_BORROWING_PERIOD_DAYS,
    FINE_PER_OVERDUE_DAY,
    MAX_BOOKS_PER_MEMBER,
    MAX_RENEWALS,
)
from database import DatabaseManager
from models.borrowing import Borrowing
from utils.logger import log_event


class BorrowingService:
    """
    Circulation service managing borrowings, returns, and renewals.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def _generate_borrowing_id(self) -> str:
        """Generate unique human-readable Borrowing ID (e.g. BRW202608270001)."""
        today_str = datetime.date.today().strftime("%Y%m%d")
        prefix = f"BRW{today_str}"
        row = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE borrowing_id LIKE ?",
            (f"{prefix}%",)
        )
        count = row["count"] + 1
        return f"{prefix}{count:04d}"

    def _borrowing_query_base(self) -> str:
        return """
            SELECT 
                bw.*,
                m.full_name as member_name,
                m.member_id as member_code,
                b.title as book_title,
                b.isbn as book_isbn
            FROM borrowings bw
            JOIN members m ON bw.member_id = m.id
            JOIN books b ON bw.book_id = b.id
        """

    def issue_book(self, member_identifier: str, book_identifier: str) -> Tuple[bool, str, Optional[Borrowing]]:
        """
        Issue a book to a member with strict business rule validation and atomic transaction.
        member_identifier: member_id code or username or DB id
        book_identifier: ISBN or DB id
        """
        # 1. Fetch Member
        member_row = self.db.fetch_one(
            "SELECT * FROM members WHERE member_id = ? COLLATE NOCASE OR username = ? COLLATE NOCASE OR id = ?",
            (member_identifier, member_identifier, member_identifier)
        )
        if not member_row:
            return False, f"Member '{member_identifier}' not found in the system.", None

        if member_row["status"] != "Active":
            return False, f"Member '{member_row['full_name']}' is BLOCKED and cannot borrow books.", None

        member_db_id = member_row["id"]

        # 2. Fetch Book
        clean_isbn = book_identifier.strip().replace("-", "").replace(" ", "")
        book_row = self.db.fetch_one(
            "SELECT * FROM books WHERE isbn = ? OR id = ?",
            (clean_isbn, book_identifier)
        )
        if not book_row:
            return False, f"Book '{book_identifier}' not found in the catalog.", None

        book_db_id = book_row["id"]

        # 3. Check Stock Availability
        if book_row["available_quantity"] <= 0:
            return False, f"Book '{book_row['title']}' is currently OUT OF STOCK (Available: 0).", None

        # 4. Check Member Borrowing Limit
        active_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE member_id = ? AND status = 'Issued'",
            (member_db_id,)
        )["count"]

        if active_count >= MAX_BOOKS_PER_MEMBER:
            return (
                False,
                f"Borrowing limit reached! Maximum allowed active books per member is {MAX_BOOKS_PER_MEMBER}. (Current: {active_count})",
                None
            )

        # 5. Check Duplicate Borrowing
        duplicate_active = self.db.fetch_one(
            "SELECT id FROM borrowings WHERE member_id = ? AND book_id = ? AND status = 'Issued'",
            (member_db_id, book_db_id)
        )
        if duplicate_active:
            return False, f"Member already has an active borrowed copy of '{book_row['title']}'.", None

        # 6. Execute Transaction
        issue_date = datetime.date.today()
        due_date = issue_date + datetime.timedelta(days=DEFAULT_BORROWING_PERIOD_DAYS)
        borrowing_id_code = self._generate_borrowing_id()

        try:
            with self.db.transaction() as conn:
                # Insert borrowing record
                conn.execute(
                    """
                    INSERT INTO borrowings (
                        borrowing_id, member_id, book_id, issue_date, due_date, renewal_count, status
                    ) VALUES (?, ?, ?, ?, ?, 0, 'Issued')
                    """,
                    (
                        borrowing_id_code,
                        member_db_id,
                        book_db_id,
                        issue_date.strftime("%Y-%m-%d"),
                        due_date.strftime("%Y-%m-%d")
                    )
                )

                # Decrement available quantity
                new_avail = book_row["available_quantity"] - 1
                new_status = "Available" if new_avail > 0 else "Unavailable"
                conn.execute(
                    "UPDATE books SET available_quantity = ?, status = ? WHERE id = ?",
                    (new_avail, new_status, book_db_id)
                )

            log_event(
                "INFO",
                f"Book issued: '{book_row['title']}' to {member_row['full_name']} [{borrowing_id_code}]"
            )

            row = self.db.fetch_one(
                f"{self._borrowing_query_base()} WHERE bw.borrowing_id = ?",
                (borrowing_id_code,)
            )
            return True, "Book issued successfully!", Borrowing.from_row(row)

        except Exception as e:
            log_event("ERROR", f"Failed to issue book: {e}")
            return False, f"Failed to issue book due to transaction error: {e}", None

    def get_borrowing_by_code(self, borrowing_code: str) -> Optional[Borrowing]:
        row = self.db.fetch_one(
            f"{self._borrowing_query_base()} WHERE bw.borrowing_id = ? COLLATE NOCASE",
            (borrowing_code.strip(),)
        )
        return Borrowing.from_row(row) if row else None

    def return_book(self, borrowing_code: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Return an issued book, calculate overdue fine, and adjust inventory.
        """
        borrowing = self.get_borrowing_by_code(borrowing_code)
        if not borrowing:
            return False, f"Borrowing record '{borrowing_code}' not found.", None

        if borrowing.status == "Returned":
            return False, f"This book has already been returned on {borrowing.return_date}.", None

        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        # Calculate overdue days and fine
        due_date = datetime.datetime.strptime(borrowing.due_date, "%Y-%m-%d").date()
        overdue_days = max(0, (today - due_date).days)
        fine_amount = Decimal(overdue_days) * FINE_PER_OVERDUE_DAY

        try:
            with self.db.transaction() as conn:
                # Update borrowing record
                conn.execute(
                    "UPDATE borrowings SET return_date = ?, status = 'Returned' WHERE id = ?",
                    (today_str, borrowing.id)
                )

                # Increment book available quantity
                conn.execute(
                    """
                    UPDATE books
                    SET available_quantity = available_quantity + 1, status = 'Available'
                    WHERE id = ?
                    """,
                    (borrowing.book_id,)
                )

                # If fine applies, record fine
                fine_id = None
                if fine_amount > Decimal("0.00"):
                    cursor = conn.execute(
                        """
                        INSERT INTO fines (borrowing_id, member_id, amount, reason, status)
                        VALUES (?, ?, ?, ?, 'Unpaid')
                        """,
                        (
                            borrowing.id,
                            borrowing.member_id,
                            float(fine_amount),
                            f"Overdue return: {overdue_days} day(s) overdue"
                        )
                    )
                    fine_id = cursor.lastrowid
                    log_event("WARNING", f"Fine generated: Rs. {fine_amount} for member ID {borrowing.member_id}")

            log_event("INFO", f"Book returned: {borrowing.book_title} (Borrowing: {borrowing_code})")

            return_summary = {
                "borrowing_id": borrowing.borrowing_id,
                "book_title": borrowing.book_title,
                "member_name": borrowing.member_name,
                "issue_date": borrowing.issue_date,
                "due_date": borrowing.due_date,
                "return_date": today_str,
                "overdue_days": overdue_days,
                "fine_amount": fine_amount,
                "fine_id": fine_id
            }
            return True, "Book returned successfully!", return_summary

        except Exception as e:
            log_event("ERROR", f"Error returning book: {e}")
            return False, f"Failed to return book due to transaction error: {e}", None

    def renew_book(self, borrowing_code: str, member_id_num: Optional[int] = None) -> Tuple[bool, str, Optional[Borrowing]]:
        """
        Renew an issued book if renewal limit is not exceeded and book is not overdue.
        """
        borrowing = self.get_borrowing_by_code(borrowing_code)
        if not borrowing:
            return False, f"Borrowing record '{borrowing_code}' not found.", None

        if member_id_num and borrowing.member_id != member_id_num:
            return False, "You can only renew books issued under your own account.", None

        if borrowing.status != "Issued":
            return False, f"Cannot renew this book because its status is '{borrowing.status}'.", None

        # Check member status
        member = self.db.fetch_one("SELECT status FROM members WHERE id = ?", (borrowing.member_id,))
        if not member or member["status"] != "Active":
            return False, "Cannot renew book. Member account is not active.", None

        # Check Renewal Limit
        if borrowing.renewal_count >= MAX_RENEWALS:
            return False, f"Maximum renewals reached! (Allowed: {MAX_RENEWALS}, Used: {borrowing.renewal_count})", None

        # Check if already overdue
        today = datetime.date.today()
        due_date = datetime.datetime.strptime(borrowing.due_date, "%Y-%m-%d").date()
        if today > due_date:
            days_overdue = (today - due_date).days
            return (
                False,
                f"Cannot renew an overdue book! (Due on {borrowing.due_date}, {days_overdue} day(s) overdue). Please return the book and clear any fines.",
                None
            )

        # Extend due date
        new_due_date = due_date + datetime.timedelta(days=DEFAULT_BORROWING_PERIOD_DAYS)
        new_renewal_count = borrowing.renewal_count + 1

        try:
            self.db.execute_update(
                """
                UPDATE borrowings
                SET due_date = ?, renewal_count = ?
                WHERE id = ?
                """,
                (new_due_date.strftime("%Y-%m-%d"), new_renewal_count, borrowing.id)
            )
            log_event("INFO", f"Borrowing {borrowing_code} renewed. New due date: {new_due_date}")

            updated_row = self.db.fetch_one(
                f"{self._borrowing_query_base()} WHERE bw.id = ?",
                (borrowing.id,)
            )
            return True, f"Book renewed successfully! New due date: {new_due_date.strftime('%d-%b-%Y')}", Borrowing.from_row(updated_row)

        except Exception as e:
            log_event("ERROR", f"Error renewing book: {e}")
            return False, f"Failed to renew book: {e}", None

    def get_issued_books(self) -> list[Borrowing]:
        """Fetch all currently active issued books."""
        rows = self.db.fetch_all(
            f"{self._borrowing_query_base()} WHERE bw.status = 'Issued' ORDER BY bw.due_date ASC"
        )
        return [Borrowing.from_row(r) for r in rows]

    def get_overdue_books(self) -> list[dict]:
        """
        Fetch all overdue books dynamically calculated based on today's date.
        """
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        sql = f"""
            {self._borrowing_query_base()}
            WHERE bw.status = 'Issued' AND bw.due_date < ?
            ORDER BY bw.due_date ASC
        """
        rows = self.db.fetch_all(sql, (today_str,))
        
        overdue_list = []
        for r in rows:
            b = Borrowing.from_row(r)
            days = b.calculate_overdue_days(today)
            estimated_fine = Decimal(days) * FINE_PER_OVERDUE_DAY
            overdue_list.append({
                "borrowing": b,
                "days_overdue": days,
                "estimated_fine": estimated_fine
            })
        return overdue_list

    def get_member_borrowings(self, member_id_num: int, active_only: bool = False) -> list[Borrowing]:
        """Fetch borrowings for a specific member."""
        if active_only:
            sql = f"{self._borrowing_query_base()} WHERE bw.member_id = ? AND bw.status = 'Issued' ORDER BY bw.due_date ASC"
        else:
            sql = f"{self._borrowing_query_base()} WHERE bw.member_id = ? ORDER BY bw.id DESC"
        
        rows = self.db.fetch_all(sql, (member_id_num,))
        return [Borrowing.from_row(r) for r in rows]

    def search_borrowing_history(
        self,
        query: str = "",
        status_filter: str = "ALL"
    ) -> list[Borrowing]:
        """
        Filter and search admin borrowing history.
        """
        sql = self._borrowing_query_base() + " WHERE 1=1"
        params = []

        if status_filter and status_filter.upper() != "ALL":
            if status_filter.upper() == "OVERDUE":
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                sql += " AND bw.status = 'Issued' AND bw.due_date < ?"
                params.append(today_str)
            else:
                sql += " AND bw.status = ?"
                params.append(status_filter)

        if query and query.strip():
            term = f"%{query.strip()}%"
            sql += """
                AND (
                    bw.borrowing_id LIKE ?
                    OR m.member_id LIKE ?
                    OR m.full_name LIKE ?
                    OR b.title LIKE ?
                    OR b.isbn LIKE ?
                )
            """
            params.extend([term, term, term, term, term])

        sql += " ORDER BY bw.id DESC"
        rows = self.db.fetch_all(sql, tuple(params))
        return [Borrowing.from_row(r) for r in rows]
