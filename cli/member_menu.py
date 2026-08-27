"""
Member CLI Interface Module.
Implements the interactive Member dashboard, catalog browsing, self-service circulation,
reservations, fines tracking, and profile management.
"""

from typing import Optional
from models.member import Member
from services.auth_service import AuthService
from services.book_service import BookService
from services.borrowing_service import BorrowingService
from services.fine_service import FineService
from services.member_service import MemberService
from services.reservation_service import ReservationService
from utils.helpers import (
    BOLD,
    CYAN,
    RESET,
    clear_screen,
    format_currency,
    format_date,
    pause,
    print_banner,
    print_error,
    print_info,
    print_key_value_card,
    print_success,
    print_table,
    print_warning,
    prompt_choice,
    prompt_confirmation,
    prompt_string,
)
from utils.security import get_secure_password


class MemberMenu:
    """
    Personalized Member CLI Portal.
    """
    def __init__(self, member: Member):
        self.member = member
        self.book_service = BookService()
        self.member_service = MemberService()
        self.borrowing_service = BorrowingService()
        self.fine_service = FineService()
        self.reservation_service = ReservationService()
        self.auth_service = AuthService()

    def _refresh_member_data(self) -> None:
        """Fetch updated member model from database."""
        updated = self.member_service.get_member_by_id(self.member.id)
        if updated:
            self.member = updated

    def run(self) -> None:
        """Main member portal loop."""
        while True:
            self._refresh_member_data()
            if not self.member.is_active:
                clear_screen()
                print_error("Your account has been BLOCKED by the administrator. Session terminated.")
                pause()
                break

            clear_screen()
            print_banner(f"MEMBER DASHBOARD - WELCOME, {self.member.full_name.upper()}")
            
            # Dynamic stats
            stats = self.member_service.get_member_stats(self.member.id)
            print(f" Member ID: {BOLD}{self.member.member_id}{RESET} | Status: {BOLD}{self.member.status}{RESET}")
            print(f" Books Currently Borrowed : {BOLD}{stats['borrowed_books']}{RESET} / 5")
            print(f" Overdue Books            : {BOLD}{stats['overdue_books']}{RESET}")
            print(f" Pending Reservations     : {BOLD}{stats['pending_reservations']}{RESET}")
            print(f" Unpaid Fines             : {BOLD}{format_currency(stats['unpaid_fine'])}{RESET}")
            print("-" * 60)

            print(" 1. My Profile")
            print(" 2. Search Books")
            print(" 3. Available Books")
            print(" 4. Borrow Book")
            print(" 5. My Borrowed Books (Active)")
            print(" 6. Return Book")
            print(" 7. Renew Book")
            print(" 8. Borrowing History")
            print(" 9. My Reservations")
            print("10. My Fines")
            print("11. Change Password")
            print("12. Logout")
            print("-" * 60)

            choice = prompt_choice("Enter your choice (1-12): ")

            if choice == "1":
                self.view_profile()
            elif choice == "2":
                self.search_books()
            elif choice == "3":
                self.view_available_books()
            elif choice == "4":
                self.borrow_book()
            elif choice == "5":
                self.view_active_borrowed_books()
            elif choice == "6":
                self.return_book()
            elif choice == "7":
                self.renew_book()
            elif choice == "8":
                self.view_borrowing_history()
            elif choice == "9":
                self.manage_reservations()
            elif choice == "10":
                self.view_fines()
            elif choice == "11":
                self.change_password()
            elif choice == "12":
                print_info("Logging out from Member session...")
                pause()
                break
            else:
                print_error("Invalid choice. Please select a number between 1 and 12.")
                pause()

    # =========================================================================
    # 1. PROFILE
    # =========================================================================
    def view_profile(self) -> None:
        while True:
            clear_screen()
            print_banner("MY PROFILE DETAILS")
            self._refresh_member_data()
            print_key_value_card("MEMBER INFORMATION", self.member.to_dict())

            print("1. Update Contact Information")
            print("2. Back to Member Dashboard")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                new_name = prompt_string("Full Name", default=self.member.full_name)
                new_phone = prompt_string("Phone", default=self.member.phone)
                new_email = prompt_string("Email", default=self.member.email)
                new_addr = prompt_string("Address", default=self.member.address)

                if prompt_confirmation("Save profile updates?"):
                    success, msg = self.member_service.update_profile(
                        member_id_num=self.member.id,
                        full_name=new_name,
                        phone=new_phone,
                        email=new_email,
                        address=new_addr
                    )
                    if success:
                        print_success(msg)
                        self._refresh_member_data()
                    else:
                        print_error(msg)
                pause()
            elif choice == "2":
                break
            else:
                print_error("Invalid option.")
                pause()

    # =========================================================================
    # 2. SEARCH BOOKS
    # =========================================================================
    def search_books(self) -> None:
        clear_screen()
        print_banner("SEARCH LIBRARY CATALOG")
        q = prompt_string("Enter search keyword (Title, ISBN, Author, Category)")
        books = self.book_service.search_books(q)
        headers = ["ISBN", "Title", "Author", "Category", "Available Copies", "Shelf", "Status"]
        rows = [
            [b.isbn, b.title, b.author_name, b.category_name, b.available_quantity, b.shelf_location, b.status]
            for b in books
        ]
        print_table(headers, rows, f"No books found matching '{q}'.")

        # Quick action: Offer to reserve if unavailable
        if books:
            prompt_isbn = prompt_string("Enter ISBN for details / reservation (or press Enter to skip)", required=False)
            if prompt_isbn:
                selected = self.book_service.get_book_by_isbn(prompt_isbn)
                if selected:
                    self._show_book_detail_and_reserve(selected)
                else:
                    print_error("Book ISBN not found.")
                    pause()
        else:
            pause()

    def _show_book_detail_and_reserve(self, book) -> None:
        clear_screen()
        print_key_value_card("BOOK DETAILS", book.to_dict())
        if book.available_quantity == 0:
            print_warning("This book is currently OUT OF STOCK.")
            if prompt_confirmation("Would you like to reserve this book?"):
                success, msg, res = self.reservation_service.create_reservation(self.member.id, book.isbn)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
                pause()
        else:
            if prompt_confirmation("Would you like to borrow this book now?"):
                success, msg, borrowing = self.borrowing_service.issue_book(str(self.member.id), book.isbn)
                if success:
                    print_success(msg)
                    receipt = {
                        "Borrowing ID": borrowing.borrowing_id,
                        "Book": borrowing.book_title,
                        "Issue Date": format_date(borrowing.issue_date),
                        "Due Date": format_date(borrowing.due_date)
                    }
                    print_key_value_card("BORROWING CONFIRMATION", receipt)
                else:
                    print_error(msg)
                pause()

    # =========================================================================
    # 3. AVAILABLE BOOKS
    # =========================================================================
    def view_available_books(self) -> None:
        clear_screen()
        print_banner("BOOKS AVAILABLE FOR BORROWING")
        books = self.book_service.get_available_books()
        headers = ["ISBN", "Title", "Author", "Category", "Available", "Shelf"]
        rows = [
            [b.isbn, b.title, b.author_name, b.category_name, b.available_quantity, b.shelf_location]
            for b in books
        ]
        print_table(headers, rows, "No books currently available.")
        pause()

    # =========================================================================
    # 4. BORROW BOOK
    # =========================================================================
    def borrow_book(self) -> None:
        clear_screen()
        print_banner("BORROW A BOOK")
        isbn = prompt_string("Enter Book ISBN or Book ID")

        book = self.book_service.get_book_by_isbn(isbn) or (
            self.book_service.get_book_by_id(int(isbn)) if isbn.isdigit() else None
        )
        if not book:
            print_error(f"Book '{isbn}' not found in catalog.")
            pause()
            return

        if book.available_quantity <= 0:
            print_warning(f"'{book.title}' is currently OUT OF STOCK.")
            if prompt_confirmation("Would you like to place a reservation instead?"):
                success, msg, res = self.reservation_service.create_reservation(self.member.id, book.isbn)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
            pause()
            return

        print(f"\nBook Title : {BOLD}{book.title}{RESET}")
        print(f"Author     : {book.author_name}")
        print(f"Category   : {book.category_name}")
        print(f"Available  : {book.available_quantity} copies\n")

        if not prompt_confirmation("Confirm borrowing this book?"):
            print_info("Borrowing cancelled.")
            pause()
            return

        success, msg, borrowing = self.borrowing_service.issue_book(str(self.member.id), book.isbn)
        if success:
            print_success(msg)
            receipt = {
                "Borrowing ID": borrowing.borrowing_id,
                "Book Title": borrowing.book_title,
                "Issue Date": format_date(borrowing.issue_date),
                "Due Date": format_date(borrowing.due_date),
                "Status": borrowing.status
            }
            print_key_value_card("BORROWING RECEIPT", receipt)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 5. MY BORROWED BOOKS
    # =========================================================================
    def view_active_borrowed_books(self) -> None:
        clear_screen()
        print_banner("MY CURRENTLY BORROWED BOOKS")
        borrowings = self.borrowing_service.get_member_borrowings(self.member.id, active_only=True)
        headers = ["Borrowing ID", "Book Title", "ISBN", "Issue Date", "Due Date", "Renewals Used"]
        rows = [
            [b.borrowing_id, b.book_title, b.book_isbn, format_date(b.issue_date), format_date(b.due_date), f"{b.renewal_count} / 2"]
            for b in borrowings
        ]
        print_table(headers, rows, "You have no active borrowed books.")
        pause()

    # =========================================================================
    # 6. RETURN BOOK
    # =========================================================================
    def return_book(self) -> None:
        clear_screen()
        print_banner("RETURN A BORROWED BOOK")
        borrowings = self.borrowing_service.get_member_borrowings(self.member.id, active_only=True)
        if not borrowings:
            print_info("You have no active borrowed books to return.")
            pause()
            return

        headers = ["Borrowing ID", "Book Title", "Issue Date", "Due Date"]
        rows = [[b.borrowing_id, b.book_title, format_date(b.issue_date), format_date(b.due_date)] for b in borrowings]
        print_table(headers, rows)

        code = prompt_string("Enter Borrowing ID to return")
        # Validate that the borrowing belongs to this member
        target_b = next((b for b in borrowings if b.borrowing_id.upper() == code.upper()), None)
        if not target_b:
            print_error("Invalid Borrowing ID. Please choose from your active borrowings above.")
            pause()
            return

        if not prompt_confirmation(f"Confirm return of '{target_b.book_title}'?"):
            print_info("Return cancelled.")
            pause()
            return

        success, msg, summary = self.borrowing_service.return_book(target_b.borrowing_id)
        if success:
            print_success(msg)
            return_card = {
                "Borrowing ID": summary["borrowing_id"],
                "Book": summary["book_title"],
                "Return Date": format_date(summary["return_date"]),
                "Days Overdue": summary["overdue_days"],
                "Fine Incurred": format_currency(summary["fine_amount"])
            }
            print_key_value_card("RETURN SUMMARY", return_card)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 7. RENEW BOOK
    # =========================================================================
    def renew_book(self) -> None:
        clear_screen()
        print_banner("RENEW A BORROWED BOOK")
        borrowings = self.borrowing_service.get_member_borrowings(self.member.id, active_only=True)
        if not borrowings:
            print_info("You have no active borrowed books to renew.")
            pause()
            return

        headers = ["Borrowing ID", "Book Title", "Due Date", "Renewals Used"]
        rows = [[b.borrowing_id, b.book_title, format_date(b.due_date), f"{b.renewal_count} / 2"] for b in borrowings]
        print_table(headers, rows)

        code = prompt_string("Enter Borrowing ID to renew")
        target_b = next((b for b in borrowings if b.borrowing_id.upper() == code.upper()), None)
        if not target_b:
            print_error("Invalid Borrowing ID. Please choose from your active borrowings above.")
            pause()
            return

        if not prompt_confirmation(f"Extend due date for '{target_b.book_title}'?"):
            print_info("Renewal cancelled.")
            pause()
            return

        success, msg, updated = self.borrowing_service.renew_book(target_b.borrowing_id, member_id_num=self.member.id)
        if success:
            print_success(msg)
            card = {
                "Borrowing ID": updated.borrowing_id,
                "Book": updated.book_title,
                "New Due Date": format_date(updated.due_date),
                "Renewals Used": f"{updated.renewal_count} / 2"
            }
            print_key_value_card("RENEWAL DETAILS", card)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 8. BORROWING HISTORY
    # =========================================================================
    def view_borrowing_history(self) -> None:
        clear_screen()
        print_banner("MY COMPLETE BORROWING HISTORY")
        history = self.borrowing_service.get_member_borrowings(self.member.id, active_only=False)
        headers = ["Borrowing ID", "Book Title", "ISBN", "Issue Date", "Due Date", "Return Date", "Status"]
        rows = [
            [
                b.borrowing_id,
                b.book_title,
                b.book_isbn,
                format_date(b.issue_date),
                format_date(b.due_date),
                format_date(b.return_date) if b.return_date else "-",
                b.status
            ]
            for b in history
        ]
        print_table(headers, rows, "No borrowing history on record.")
        pause()

    # =========================================================================
    # 9. RESERVATIONS
    # =========================================================================
    def manage_reservations(self) -> None:
        while True:
            clear_screen()
            print_banner("MY BOOK RESERVATIONS")
            reservations = self.reservation_service.get_member_reservations(self.member.id)
            headers = ["Reservation ID", "Book Title", "ISBN", "Reserved Date", "Status"]
            rows = [
                [r.reservation_id, r.book_title, r.book_isbn, format_date(r.reservation_date), r.status]
                for r in reservations
            ]
            print_table(headers, rows, "You currently have no reservations.")

            print("1. Reserve an Unavailable Book")
            print("2. Cancel a Pending Reservation")
            print("3. Back to Member Dashboard")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                isbn = prompt_string("Enter Book ISBN or ID to reserve")
                success, msg, res = self.reservation_service.create_reservation(self.member.id, isbn)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
                pause()
            elif choice == "2":
                res_code = prompt_string("Enter Reservation ID to cancel")
                if prompt_confirmation(f"Cancel reservation '{res_code}'?"):
                    success, msg = self.reservation_service.cancel_reservation(res_code, member_id_num=self.member.id)
                    if success:
                        print_success(msg)
                    else:
                        print_error(msg)
                pause()
            elif choice == "3":
                break
            else:
                print_error("Invalid option.")
                pause()

    # =========================================================================
    # 10. MY FINES
    # =========================================================================
    def view_fines(self) -> None:
        clear_screen()
        print_banner("MY FINES & PENALTIES")
        fines = self.fine_service.get_member_fines(self.member.id)
        headers = ["Fine ID", "Borrowing ID", "Book Title", "Amount", "Reason", "Status", "Date Incurred", "Paid On"]
        rows = [
            [
                f.id,
                f.borrowing_code or "-",
                f.book_title or "-",
                format_currency(f.amount),
                f.reason,
                f.status,
                format_date(f.created_at),
                format_date(f.paid_at) if f.paid_at else "-"
            ]
            for f in fines
        ]
        print_table(headers, rows, "No fines on record. Excellent!")
        
        unpaid_sum = sum([f.amount for f in fines if f.status == "Unpaid"])
        if unpaid_sum > 0:
            print_warning(f"Total Unpaid Fines: {format_currency(unpaid_sum)}. Please clear fines with the librarian at the desk.")
        pause()

    # =========================================================================
    # 11. CHANGE PASSWORD
    # =========================================================================
    def change_password(self) -> None:
        clear_screen()
        print_banner("CHANGE ACCOUNT PASSWORD")
        old_pwd = get_secure_password("Enter current password: ")
        new_pwd = get_secure_password("Enter new password: ")
        confirm_pwd = get_secure_password("Confirm new password: ")

        if not prompt_confirmation("Confirm password update?"):
            print_info("Password change cancelled.")
            pause()
            return

        success, msg = self.auth_service.change_password(
            user_type="member",
            user_id=self.member.id,
            old_password=old_pwd,
            new_password=new_pwd,
            confirm_new_password=confirm_pwd
        )
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()
