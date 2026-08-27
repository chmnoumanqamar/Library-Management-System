"""
Report Generator & CSV Export Engine.
Generates statistical analytics and exports system records to CSV.
"""

import csv
import datetime
from decimal import Decimal
import os
from typing import Optional, Tuple
from config import EXPORTS_DIR
from database import DatabaseManager
from utils.logger import log_event


class ReportGenerator:
    """
    Reporting and data analytics engine for Library Management System.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def get_dashboard_stats(self) -> dict:
        """
        Calculate dynamic real-time administrative dashboard statistics.
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        # Book statistics
        book_stats = self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_titles,
                COALESCE(SUM(quantity), 0) as total_copies,
                COALESCE(SUM(available_quantity), 0) as available_copies
            FROM books
            """
        )
        total_titles = book_stats["total_titles"]
        total_copies = book_stats["total_copies"]
        available_copies = book_stats["available_copies"]
        issued_copies = total_copies - available_copies

        # Overdue borrowings
        overdue_row = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE status = 'Issued' AND due_date < ?",
            (today_str,)
        )
        overdue_books = overdue_row["count"]

        # Member statistics
        member_stats = self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_members,
                COALESCE(SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END), 0) as active_members,
                COALESCE(SUM(CASE WHEN status = 'Blocked' THEN 1 ELSE 0 END), 0) as blocked_members
            FROM members
            """
        )
        total_members = member_stats["total_members"]
        active_members = member_stats["active_members"]
        blocked_members = member_stats["blocked_members"]

        # Pending reservations
        pending_res_row = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM reservations WHERE status = 'Pending'"
        )
        pending_reservations = pending_res_row["count"]

        # Unpaid fines
        fine_row = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount), 0) as unpaid_sum FROM fines WHERE status = 'Unpaid'"
        )
        unpaid_fines = Decimal(str(fine_row["unpaid_sum"]))

        return {
            "total_titles": total_titles,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies,
            "overdue_books": overdue_books,
            "total_members": total_members,
            "active_members": active_members,
            "blocked_members": blocked_members,
            "pending_reservations": pending_reservations,
            "unpaid_fines": unpaid_fines
        }

    # =========================================================================
    # DETAILED REPORTS
    # =========================================================================
    def get_book_report(self) -> dict:
        stats = self.get_dashboard_stats()
        unavailable_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM books WHERE available_quantity = 0"
        )["count"]
        
        books = self.db.fetch_all(
            """
            SELECT 
                b.id, b.isbn, b.title, a.name as author, c.name as category,
                p.name as publisher, b.publication_year, b.edition,
                b.quantity, b.available_quantity, b.shelf_location, b.status
            FROM books b
            LEFT JOIN authors a ON b.author_id = a.id
            LEFT JOIN categories c ON b.category_id = c.id
            LEFT JOIN publishers p ON b.publisher_id = p.id
            ORDER BY b.title ASC
            """
        )
        return {
            "summary": {
                "Total Titles": stats["total_titles"],
                "Total Copies": stats["total_copies"],
                "Available Copies": stats["available_copies"],
                "Issued Copies": stats["issued_copies"],
                "Out of Stock Titles": unavailable_count
            },
            "records": books
        }

    def get_member_report(self) -> dict:
        stats = self.get_dashboard_stats()
        members = self.db.fetch_all(
            """
            SELECT id, member_id, full_name, cnic, phone, email, address, username, status, created_at
            FROM members
            ORDER BY full_name ASC
            """
        )
        return {
            "summary": {
                "Total Members": stats["total_members"],
                "Active Members": stats["active_members"],
                "Blocked Members": stats["blocked_members"]
            },
            "records": members
        }

    def get_borrowing_report(self) -> dict:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        total = self.db.fetch_one("SELECT COUNT(*) as count FROM borrowings")["count"]
        active = self.db.fetch_one("SELECT COUNT(*) as count FROM borrowings WHERE status = 'Issued'")["count"]
        returned = self.db.fetch_one("SELECT COUNT(*) as count FROM borrowings WHERE status = 'Returned'")["count"]
        overdue = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE status = 'Issued' AND due_date < ?",
            (today_str,)
        )["count"]

        borrowings = self.db.fetch_all(
            """
            SELECT 
                bw.borrowing_id, m.member_id as member_code, m.full_name as member_name,
                b.isbn, b.title as book_title, bw.issue_date, bw.due_date,
                bw.return_date, bw.renewal_count, bw.status
            FROM borrowings bw
            JOIN members m ON bw.member_id = m.id
            JOIN books b ON bw.book_id = b.id
            ORDER BY bw.id DESC
            """
        )
        return {
            "summary": {
                "Total Borrowings": total,
                "Currently Active": active,
                "Returned Books": returned,
                "Overdue Books": overdue
            },
            "records": borrowings
        }

    def get_fine_report(self) -> dict:
        fine_stats = self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_fines,
                COALESCE(SUM(amount), 0) as total_amount,
                COALESCE(SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END), 0) as paid_count,
                COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) as paid_amount,
                COALESCE(SUM(CASE WHEN status = 'Unpaid' THEN 1 ELSE 0 END), 0) as unpaid_count,
                COALESCE(SUM(CASE WHEN status = 'Unpaid' THEN amount ELSE 0 END), 0) as unpaid_amount
            FROM fines
            """
        )
        fines = self.db.fetch_all(
            """
            SELECT 
                f.id, bw.borrowing_id as borrowing_code, m.member_id as member_code,
                m.full_name as member_name, f.amount, f.reason, f.status,
                f.created_at, f.paid_at
            FROM fines f
            JOIN members m ON f.member_id = m.id
            LEFT JOIN borrowings bw ON f.borrowing_id = bw.id
            ORDER BY f.id DESC
            """
        )
        return {
            "summary": {
                "Total Fine Records": fine_stats["total_fines"],
                "Total Fine Amount": Decimal(str(fine_stats["total_amount"])),
                "Paid Fines Count": fine_stats["paid_count"],
                "Collected Amount": Decimal(str(fine_stats["paid_amount"])),
                "Unpaid Fines Count": fine_stats["unpaid_count"],
                "Unpaid Amount": Decimal(str(fine_stats["unpaid_amount"]))
            },
            "records": fines
        }

    def get_reservation_report(self) -> dict:
        res_stats = self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_reservations,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) as pending_count,
                COALESCE(SUM(CASE WHEN status = 'Fulfilled' THEN 1 ELSE 0 END), 0) as fulfilled_count,
                COALESCE(SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END), 0) as cancelled_count
            FROM reservations
            """
        )
        reservations = self.db.fetch_all(
            """
            SELECT 
                r.reservation_id, m.member_id as member_code, m.full_name as member_name,
                b.isbn, b.title as book_title, r.reservation_date, r.status, r.created_at
            FROM reservations r
            JOIN members m ON r.member_id = m.id
            JOIN books b ON r.book_id = b.id
            ORDER BY r.id DESC
            """
        )
        return {
            "summary": {
                "Total Reservations": res_stats["total_reservations"],
                "Pending Reservations": res_stats["pending_count"],
                "Fulfilled Reservations": res_stats["fulfilled_count"],
                "Cancelled Reservations": res_stats["cancelled_count"]
            },
            "records": reservations
        }

    # =========================================================================
    # CSV EXPORTS
    # =========================================================================
    def _export_to_csv(self, filename: str, headers: list[str], rows: list[list[any]]) -> Tuple[bool, str, str]:
        """Export dataset to CSV in the exports directory."""
        file_path = os.path.join(EXPORTS_DIR, filename)
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in rows:
                    writer.writerow([str(item) if item is not None else "" for item in r])
            
            log_event("INFO", f"Report exported to CSV: {file_path}")
            return True, f"Report exported successfully.\nFile: {file_path}", file_path
        except Exception as e:
            log_event("ERROR", f"Error exporting CSV to {filename}: {e}")
            return False, f"Failed to export CSV: {e}", ""

    def export_books_csv(self, filename: str = "books_report.csv") -> Tuple[bool, str, str]:
        report = self.get_book_report()
        headers = [
            "ID", "ISBN", "Title", "Author", "Category", "Publisher",
            "Publication Year", "Edition", "Quantity", "Available Quantity",
            "Shelf Location", "Status"
        ]
        rows = []
        for r in report["records"]:
            rows.append([
                r["id"], r["isbn"], r["title"], r["author"] or "",
                r["category"] or "", r["publisher"] or "",
                r["publication_year"], r["edition"] or "",
                r["quantity"], r["available_quantity"],
                r["shelf_location"] or "", r["status"]
            ])
        return self._export_to_csv(filename, headers, rows)

    def export_members_csv(self, filename: str = "members_report.csv") -> Tuple[bool, str, str]:
        report = self.get_member_report()
        headers = [
            "ID", "Member ID", "Full Name", "CNIC", "Phone", "Email",
            "Address", "Username", "Status", "Created At"
        ]
        rows = []
        for r in report["records"]:
            rows.append([
                r["id"], r["member_id"], r["full_name"], r["cnic"],
                r["phone"], r["email"], r["address"], r["username"],
                r["status"], r["created_at"]
            ])
        return self._export_to_csv(filename, headers, rows)

    def export_borrowings_csv(self, filename: str = "borrowings_report.csv") -> Tuple[bool, str, str]:
        report = self.get_borrowing_report()
        headers = [
            "Borrowing ID", "Member ID", "Member Name", "ISBN", "Book Title",
            "Issue Date", "Due Date", "Return Date", "Renewals", "Status"
        ]
        rows = []
        for r in report["records"]:
            rows.append([
                r["borrowing_id"], r["member_code"], r["member_name"],
                r["isbn"], r["book_title"], r["issue_date"],
                r["due_date"], r["return_date"] or "",
                r["renewal_count"], r["status"]
            ])
        return self._export_to_csv(filename, headers, rows)

    def export_fines_csv(self, filename: str = "fines_report.csv") -> Tuple[bool, str, str]:
        report = self.get_fine_report()
        headers = [
            "Fine ID", "Borrowing ID", "Member ID", "Member Name",
            "Amount", "Reason", "Status", "Created At", "Paid At"
        ]
        rows = []
        for r in report["records"]:
            rows.append([
                r["id"], r["borrowing_code"] or "", r["member_code"],
                r["member_name"], f"{r['amount']:.2f}", r["reason"],
                r["status"], r["created_at"], r["paid_at"] or ""
            ])
        return self._export_to_csv(filename, headers, rows)

    def export_reservations_csv(self, filename: str = "reservations_report.csv") -> Tuple[bool, str, str]:
        report = self.get_reservation_report()
        headers = [
            "Reservation ID", "Member ID", "Member Name", "ISBN",
            "Book Title", "Reservation Date", "Status", "Created At"
        ]
        rows = []
        for r in report["records"]:
            rows.append([
                r["reservation_id"], r["member_code"], r["member_name"],
                r["isbn"], r["book_title"], r["reservation_date"],
                r["status"], r["created_at"]
            ])
        return self._export_to_csv(filename, headers, rows)
