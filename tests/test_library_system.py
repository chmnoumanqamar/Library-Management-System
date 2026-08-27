"""
Comprehensive Automated Unit & Integration Tests for Library Management System.
Tests Authentication, Catalog, Circulation, Business Rules, Fines, Reservations, and CSV Exports.
"""

import datetime
from decimal import Decimal
import os
import shutil
import tempfile
import unittest

from database import DatabaseManager
from reports.report_generator import ReportGenerator
from services.auth_service import AuthService
from services.book_service import BookService
from services.borrowing_service import BorrowingService
from services.fine_service import FineService
from services.member_service import MemberService
from services.reservation_service import ReservationService
from utils.security import hash_password, verify_password
from utils.validators import (
    validate_cnic,
    validate_email,
    validate_isbn,
    validate_name,
    validate_non_negative_decimal,
    validate_phone,
    validate_positive_int,
    validate_username,
    validate_year,
)


class TestLibraryManagementSystem(unittest.TestCase):
    """
    Complete test suite for business rules, database integrity, and workflows.
    """
    def setUp(self):
        # Create isolated temporary database file
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_library.db")

        # Reset singleton instance to point to test database
        DatabaseManager._instance = None
        self.db = DatabaseManager(self.db_path)

        # Initialize services
        self.auth_service = AuthService(self.db)
        self.book_service = BookService(self.db)
        self.member_service = MemberService(self.db)
        self.borrowing_service = BorrowingService(self.db)
        self.fine_service = FineService(self.db)
        self.reservation_service = ReservationService(self.db)
        self.report_generator = ReportGenerator(self.db)

        # Create base test author, category, publisher
        _, _, self.author = self.book_service.add_author("Martin Fowler", "Software engineering author")
        _, _, self.category = self.book_service.add_category("Programming", "Software coding literature")
        _, _, self.publisher = self.book_service.add_publisher("Addison-Wesley", "123-456", "info@aw.com", "Boston")

        # Register a base active member
        _, _, self.member = self.auth_service.register_member(
            full_name="Ali Khan",
            member_id="MEM-001",
            cnic="35202-1234567-1",
            phone="0300-1234567",
            email="ali@example.com",
            address="Lahore",
            username="alikhan",
            password="password123",
            confirm_password="password123"
        )

        # Create admin user
        pwd_hash, salt = hash_password("admin123")
        self.admin_id = self.db.execute_update(
            "INSERT INTO admins (username, password_hash, salt, full_name, email) VALUES (?, ?, ?, ?, ?)",
            ("admin", pwd_hash, salt, "Library Admin", "admin@library.edu")
        )

    def tearDown(self):
        self.db.close()
        DatabaseManager._instance = None
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. SECURITY & CRYPTOGRAPHY TESTS
    # =========================================================================
    def test_password_hashing_and_verification(self):
        password = "SecurePassword@2026"
        pwd_hash, salt = hash_password(password)
        
        self.assertTrue(verify_password(password, pwd_hash, salt))
        self.assertFalse(verify_password("WrongPassword", pwd_hash, salt))
        self.assertNotEqual(password, pwd_hash)

    # =========================================================================
    # 2. VALIDATOR TESTS
    # =========================================================================
    def test_validators(self):
        # ISBN
        self.assertTrue(validate_isbn("9780132350884")[0])
        self.assertTrue(validate_isbn("0-13-235088-2")[0])
        self.assertFalse(validate_isbn("12345")[0])

        # CNIC
        self.assertTrue(validate_cnic("35202-1234567-1")[0])
        self.assertTrue(validate_cnic("3520212345671")[0])
        self.assertTrue(validate_cnic("STU-1001")[0])
        self.assertFalse(validate_cnic("123")[0])

        # Email
        self.assertTrue(validate_email("test.user@university.edu")[0])
        self.assertFalse(validate_email("invalid-email")[0])

        # Phone
        self.assertTrue(validate_phone("03001234567")[0])
        self.assertTrue(validate_phone("+923001234567")[0])
        self.assertFalse(validate_phone("123")[0])

        # Year
        self.assertTrue(validate_year("2022")[0])
        self.assertFalse(validate_year("850")[0])
        self.assertFalse(validate_year("abc")[0])

        # Positive int & Decimal
        self.assertTrue(validate_positive_int(5)[0])
        self.assertFalse(validate_positive_int(0)[0])
        self.assertFalse(validate_positive_int(-3)[0])
        self.assertTrue(validate_non_negative_decimal("50.25")[0])
        self.assertFalse(validate_non_negative_decimal("-10")[0])

    # =========================================================================
    # 3. AUTHENTICATION TESTS
    # =========================================================================
    def test_admin_and_member_login(self):
        # Valid Admin Login
        ok, msg, admin = self.auth_service.login_admin("admin", "admin123")
        self.assertTrue(ok)
        self.assertIsNotNone(admin)
        self.assertEqual(admin.username, "admin")

        # Invalid Admin Login
        ok, msg, admin = self.auth_service.login_admin("admin", "wrongpassword")
        self.assertFalse(ok)
        self.assertIsNone(admin)

        # Valid Member Login
        ok, msg, mem = self.auth_service.login_member("alikhan", "password123")
        self.assertTrue(ok)
        self.assertEqual(mem.username, "alikhan")

        # Blocked Member Login Rejection
        self.member_service.block_member(self.member.id)
        ok, msg, mem = self.auth_service.login_member("alikhan", "password123")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", msg)

    def test_member_duplicate_registration_prevention(self):
        # Attempt to register duplicate username
        ok, msg, _ = self.auth_service.register_member(
            full_name="Duplicate User",
            member_id="MEM-002",
            cnic="42101-7654321-2",
            phone="0321-7654321",
            email="dup@example.com",
            address="Karachi",
            username="alikhan",  # duplicate
            password="password123",
            confirm_password="password123"
        )
        self.assertFalse(ok)
        self.assertIn("already taken", msg)

        # Attempt to register duplicate Member ID
        ok, msg, _ = self.auth_service.register_member(
            full_name="Duplicate User",
            member_id="MEM-001",  # duplicate
            cnic="42101-7654321-2",
            phone="0321-7654321",
            email="dup@example.com",
            address="Karachi",
            username="newuser",
            password="password123",
            confirm_password="password123"
        )
        self.assertFalse(ok)
        self.assertIn("already registered", msg)

    # =========================================================================
    # 4. BOOK & INVENTORY MANAGEMENT TESTS
    # =========================================================================
    def test_add_and_update_book(self):
        ok, msg, book = self.book_service.add_book(
            isbn="9780132350884",
            title="Clean Code",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2008,
            edition="1st",
            quantity=5,
            shelf_location="SE-101"
        )
        self.assertTrue(ok)
        self.assertEqual(book.available_quantity, 5)
        self.assertEqual(book.status, "Available")

        # Duplicate ISBN prevention
        ok2, msg2, _ = self.book_service.add_book(
            isbn="9780132350884",
            title="Clean Code 2",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2010,
            edition="2nd",
            quantity=2,
            shelf_location="SE-102"
        )
        self.assertFalse(ok2)

    def test_book_quantity_consistency_on_update(self):
        _, _, book = self.book_service.add_book(
            isbn="9781491950357",
            title="Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2020,
            edition="1st",
            quantity=3,
            shelf_location="A1"
        )

        # Issue 1 copy
        self.borrowing_service.issue_book("alikhan", book.isbn)

        # Updated book should have available_quantity = 2
        updated_book = self.book_service.get_book_by_id(book.id)
        self.assertEqual(updated_book.available_quantity, 2)

        # Update total quantity to 5 -> available should automatically become 4 (5 - 1 issued)
        ok, msg = self.book_service.update_book(
            book_id=book.id,
            title="Test Book Updated",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2020,
            edition="1st",
            new_quantity=5,
            shelf_location="A1"
        )
        self.assertTrue(ok)
        refreshed = self.book_service.get_book_by_id(book.id)
        self.assertEqual(refreshed.quantity, 5)
        self.assertEqual(refreshed.available_quantity, 4)

        # Attempt to reduce quantity below currently issued count (1) -> should fail
        ok_fail, msg_fail = self.book_service.update_book(
            book_id=book.id,
            title="Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2020,
            edition="1st",
            new_quantity=0,  # 0 < 1 issued copy
            shelf_location="A1"
        )
        self.assertFalse(ok_fail)

    # =========================================================================
    # 5. BORROWING & CIRCULATION TESTS
    # =========================================================================
    def test_book_issue_and_limit_enforcement(self):
        # Create 6 distinct books
        books = []
        for i in range(6):
            _, _, b = self.book_service.add_book(
                isbn=f"978000000000{i}",
                title=f"Book {i}",
                author_id=self.author.id,
                category_id=self.category.id,
                publisher_id=self.publisher.id,
                publication_year=2021,
                edition="1st",
                quantity=1,
                shelf_location=f"B{i}"
            )
            books.append(b)

        # Issue 5 books (up to limit)
        for i in range(5):
            ok, msg, brw = self.borrowing_service.issue_book("alikhan", books[i].isbn)
            self.assertTrue(ok, f"Failed to issue book {i}: {msg}")

        # 6th book issue must fail due to limit
        ok_6, msg_6, _ = self.borrowing_service.issue_book("alikhan", books[5].isbn)
        self.assertFalse(ok_6)
        self.assertIn("Borrowing limit reached", msg_6)

    def test_duplicate_active_borrowing_prevention(self):
        _, _, b = self.book_service.add_book(
            isbn="9781111111111",
            title="Duplicate Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2021,
            edition="1st",
            quantity=5,
            shelf_location="C1"
        )

        ok1, _, _ = self.borrowing_service.issue_book("alikhan", b.isbn)
        self.assertTrue(ok1)

        # Attempt to issue same book again to same member
        ok2, msg2, _ = self.borrowing_service.issue_book("alikhan", b.isbn)
        self.assertFalse(ok2)
        self.assertIn("already has an active borrowed copy", msg2)

    def test_return_book_and_fine_calculation(self):
        _, _, b = self.book_service.add_book(
            isbn="9782222222222",
            title="Return Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2021,
            edition="1st",
            quantity=2,
            shelf_location="D1"
        )

        ok, msg, borrowing = self.borrowing_service.issue_book("alikhan", b.isbn)
        self.assertTrue(ok)

        # Simulate overdue: set due_date to 5 days ago
        past_due = (datetime.date.today() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
        self.db.execute_update(
            "UPDATE borrowings SET due_date = ? WHERE id = ?",
            (past_due, borrowing.id)
        )

        # Return book
        ok_ret, msg_ret, summary = self.borrowing_service.return_book(borrowing.borrowing_id)
        self.assertTrue(ok_ret)
        self.assertEqual(summary["overdue_days"], 5)
        self.assertEqual(summary["fine_amount"], Decimal("100.00"))  # 5 * 20

        # Check that fine record was created
        fines = self.fine_service.get_member_fines(self.member.id)
        self.assertTrue(len(fines) >= 1)
        self.assertEqual(fines[0].status, "Unpaid")

        # Pay fine
        ok_pay, msg_pay = self.fine_service.mark_fine_as_paid(fines[0].id)
        self.assertTrue(ok_pay)

    def test_book_renewal_rules(self):
        _, _, b = self.book_service.add_book(
            isbn="9783333333333",
            title="Renewal Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2021,
            edition="1st",
            quantity=2,
            shelf_location="E1"
        )

        _, _, borrowing = self.borrowing_service.issue_book("alikhan", b.isbn)

        # 1st Renewal - should succeed
        ok1, _, b1 = self.borrowing_service.renew_book(borrowing.borrowing_id)
        self.assertTrue(ok1)
        self.assertEqual(b1.renewal_count, 1)

        # 2nd Renewal - should succeed
        ok2, _, b2 = self.borrowing_service.renew_book(borrowing.borrowing_id)
        self.assertTrue(ok2)
        self.assertEqual(b2.renewal_count, 2)

        # 3rd Renewal - should fail (max 2 renewals)
        ok3, msg3, _ = self.borrowing_service.renew_book(borrowing.borrowing_id)
        self.assertFalse(ok3)
        self.assertIn("Maximum renewals reached", msg3)

    # =========================================================================
    # 6. RESERVATION TESTS
    # =========================================================================
    def test_reservations_workflow(self):
        _, _, b = self.book_service.add_book(
            isbn="9784444444444",
            title="Reservation Test Book",
            author_id=self.author.id,
            category_id=self.category.id,
            publisher_id=self.publisher.id,
            publication_year=2022,
            edition="1st",
            quantity=1,
            shelf_location="F1"
        )

        # Create reservation
        ok, msg, res = self.reservation_service.create_reservation(self.member.id, b.isbn)
        self.assertTrue(ok)
        self.assertEqual(res.status, "Pending")

        # Duplicate reservation prevention
        ok_dup, msg_dup, _ = self.reservation_service.create_reservation(self.member.id, b.isbn)
        self.assertFalse(ok_dup)

        # Fulfill reservation
        ok_ful, msg_ful = self.reservation_service.fulfill_reservation(res.reservation_id)
        self.assertTrue(ok_ful)

    # =========================================================================
    # 7. REPORTS & CSV EXPORT TESTS
    # =========================================================================
    def test_reports_and_csv_generation(self):
        dashboard_stats = self.report_generator.get_dashboard_stats()
        self.assertIn("total_titles", dashboard_stats)
        self.assertIn("total_copies", dashboard_stats)

        # Test CSV export methods
        ok_b, _, path_b = self.report_generator.export_books_csv("test_books.csv")
        self.assertTrue(ok_b)
        self.assertTrue(os.path.exists(path_b))

        ok_m, _, path_m = self.report_generator.export_members_csv("test_members.csv")
        self.assertTrue(ok_m)
        self.assertTrue(os.path.exists(path_m))

        ok_bw, _, path_bw = self.report_generator.export_borrowings_csv("test_borrowings.csv")
        self.assertTrue(ok_bw)
        self.assertTrue(os.path.exists(path_bw))


if __name__ == "__main__":
    unittest.main()
