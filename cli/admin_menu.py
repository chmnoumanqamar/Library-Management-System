"""
Admin CLI Interface Module.
Implements the interactive Administrative dashboard, catalog management, circulation,
fines processing, reservations handling, and reporting menus.
"""

from decimal import Decimal
from typing import Optional
from models.admin import Admin
from reports.report_generator import ReportGenerator
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
    print_section,
    print_success,
    print_table,
    print_warning,
    prompt_choice,
    prompt_confirmation,
    prompt_string,
)
from utils.validators import (
    validate_cnic,
    validate_email,
    validate_isbn,
    validate_name,
    validate_phone,
    validate_positive_int,
    validate_year,
)


class AdminMenu:
    """
    Comprehensive Admin CLI console.
    """
    def __init__(self, admin: Admin):
        self.admin = admin
        self.book_service = BookService()
        self.member_service = MemberService()
        self.borrowing_service = BorrowingService()
        self.fine_service = FineService()
        self.reservation_service = ReservationService()
        self.report_generator = ReportGenerator()
        self.auth_service = AuthService()

    def run(self) -> None:
        """Main admin loop."""
        while True:
            clear_screen()
            print_banner("ADMIN CONTROL PANEL - LIBRARY MANAGEMENT SYSTEM")
            print(f"Logged in as: {BOLD}{self.admin.full_name}{RESET} ({self.admin.username}) | Role: Administrator\n")

            print(" 1. Dashboard Statistics")
            print(" 2. Book Management")
            print(" 3. Author Management")
            print(" 4. Category Management")
            print(" 5. Publisher Management")
            print(" 6. Member Management")
            print(" 7. Issue Book")
            print(" 8. Return Book")
            print(" 9. Renew Book")
            print("10. View Issued Books")
            print("11. View Overdue Books")
            print("12. Manage Reservations")
            print("13. Manage Fines")
            print("14. Borrowing History")
            print("15. Reports & CSV Export")
            print("16. Logout")
            print("-" * 60)

            choice = prompt_choice("Enter your choice (1-16): ")

            if choice == "1":
                self.show_dashboard()
            elif choice == "2":
                self.manage_books()
            elif choice == "3":
                self.manage_authors()
            elif choice == "4":
                self.manage_categories()
            elif choice == "5":
                self.manage_publishers()
            elif choice == "6":
                self.manage_members()
            elif choice == "7":
                self.issue_book_flow()
            elif choice == "8":
                self.return_book_flow()
            elif choice == "9":
                self.renew_book_flow()
            elif choice == "10":
                self.view_issued_books()
            elif choice == "11":
                self.view_overdue_books()
            elif choice == "12":
                self.manage_reservations()
            elif choice == "13":
                self.manage_fines()
            elif choice == "14":
                self.view_borrowing_history()
            elif choice == "15":
                self.manage_reports()
            elif choice == "16":
                print_info("Logging out from Admin session...")
                pause()
                break
            else:
                print_error("Invalid choice. Please select a number between 1 and 16.")
                pause()

    # =========================================================================
    # 1. DASHBOARD
    # =========================================================================
    def show_dashboard(self) -> None:
        clear_screen()
        stats = self.report_generator.get_dashboard_stats()
        
        card_data = {
            "Total Book Titles": f"{stats['total_titles']:,}",
            "Total Book Copies": f"{stats['total_copies']:,}",
            "Available Copies": f"{stats['available_copies']:,}",
            "Currently Issued": f"{stats['issued_copies']:,}",
            "Overdue Books": f"{stats['overdue_books']:,}",
            "Total Members": f"{stats['total_members']:,}",
            "Active Members": f"{stats['active_members']:,}",
            "Blocked Members": f"{stats['blocked_members']:,}",
            "Pending Reservations": f"{stats['pending_reservations']:,}",
            "Unpaid Fines": format_currency(stats['unpaid_fines'])
        }
        print_key_value_card("REAL-TIME LIBRARY METRICS", card_data, width=58)
        pause()

    # =========================================================================
    # 2. BOOK MANAGEMENT
    # =========================================================================
    def manage_books(self) -> None:
        while True:
            clear_screen()
            print_banner("BOOK MANAGEMENT")
            print("1. Add New Book")
            print("2. View All Books")
            print("3. Search Books")
            print("4. Update Book Details")
            print("5. Delete Book")
            print("6. Back to Main Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                self._add_book()
            elif choice == "2":
                self._view_all_books()
            elif choice == "3":
                self._search_books()
            elif choice == "4":
                self._update_book()
            elif choice == "5":
                self._delete_book()
            elif choice == "6":
                break
            else:
                print_error("Invalid option.")
                pause()

    def _add_book(self) -> None:
        clear_screen()
        print_banner("ADD NEW BOOK TO CATALOG")

        # Select Author
        authors = self.book_service.get_all_authors()
        if not authors:
            print_warning("No authors found! Please add an author first in Author Management.")
            pause()
            return
        
        # Select Category
        categories = self.book_service.get_all_categories()
        if not categories:
            print_warning("No categories found! Please add a category first in Category Management.")
            pause()
            return

        # Select Publisher
        publishers = self.book_service.get_all_publishers()
        if not publishers:
            print_warning("No publishers found! Please add a publisher first in Publisher Management.")
            pause()
            return

        isbn = prompt_string("Enter ISBN (10 or 13 digits)")
        valid_i, err_i = validate_isbn(isbn)
        if not valid_i:
            print_error(err_i)
            pause()
            return

        title = prompt_string("Enter Book Title")

        print("\n--- Available Authors ---")
        for a in authors:
            print(f"[{a.id}] {a.name}")
        author_id = prompt_string("Enter Author ID")
        if not author_id.isdigit():
            print_error("Invalid Author ID.")
            pause()
            return

        print("\n--- Available Categories ---")
        for c in categories:
            print(f"[{c.id}] {c.name}")
        cat_id = prompt_string("Enter Category ID")
        if not cat_id.isdigit():
            print_error("Invalid Category ID.")
            pause()
            return

        print("\n--- Available Publishers ---")
        for p in publishers:
            print(f"[{p.id}] {p.name}")
        pub_id = prompt_string("Enter Publisher ID")
        if not pub_id.isdigit():
            print_error("Invalid Publisher ID.")
            pause()
            return

        year_str = prompt_string("Enter Publication Year (e.g. 2023)")
        edition = prompt_string("Enter Edition (e.g. 1st, 2nd, Revised)", required=False, default="1st")
        qty_str = prompt_string("Enter Total Quantity")
        shelf = prompt_string("Enter Shelf Location (e.g. A-12, PRG-101)", required=False, default="General")

        success, msg, new_book = self.book_service.add_book(
            isbn=isbn,
            title=title,
            author_id=int(author_id),
            category_id=int(cat_id),
            publisher_id=int(pub_id),
            publication_year=int(year_str) if year_str.isdigit() else 0,
            edition=edition,
            quantity=int(qty_str) if qty_str.isdigit() else 0,
            shelf_location=shelf
        )

        if success:
            print_success(msg)
            print_key_value_card("NEW BOOK REGISTERED", new_book.to_dict())
        else:
            print_error(msg)
        pause()

    def _view_all_books(self) -> None:
        clear_screen()
        print_banner("LIBRARY BOOK CATALOG")
        books = self.book_service.get_all_books()
        headers = ["ID", "ISBN", "Title", "Author", "Category", "Qty", "Avail", "Shelf", "Status"]
        rows = [
            [b.id, b.isbn, b.title, b.author_name, b.category_name, b.quantity, b.available_quantity, b.shelf_location, b.status]
            for b in books
        ]
        print_table(headers, rows, "No books in catalog.")
        pause()

    def _search_books(self) -> None:
        clear_screen()
        print_banner("SEARCH BOOKS")
        query = prompt_string("Enter search keyword (Title, ISBN, Author, Category, Shelf)")
        books = self.book_service.search_books(query)
        headers = ["ID", "ISBN", "Title", "Author", "Category", "Qty", "Avail", "Shelf", "Status"]
        rows = [
            [b.id, b.isbn, b.title, b.author_name, b.category_name, b.quantity, b.available_quantity, b.shelf_location, b.status]
            for b in books
        ]
        print_table(headers, rows, f"No books found matching '{query}'.")
        pause()

    def _update_book(self) -> None:
        clear_screen()
        print_banner("UPDATE BOOK DETAILS")
        book_id_str = prompt_string("Enter Book ID to update")
        if not book_id_str.isdigit():
            print_error("Invalid Book ID.")
            pause()
            return

        book = self.book_service.get_book_by_id(int(book_id_str))
        if not book:
            print_error(f"Book with ID {book_id_str} not found.")
            pause()
            return

        print(f"\nEditing: {BOLD}{book.title}{RESET} [ISBN: {book.isbn}]")
        print(f"Current Stock: Total = {book.quantity}, Available = {book.available_quantity}\n")

        new_title = prompt_string("Title", default=book.title)
        new_aid = prompt_string("Author ID", default=str(book.author_id))
        new_cid = prompt_string("Category ID", default=str(book.category_id))
        new_pid = prompt_string("Publisher ID", default=str(book.publisher_id))
        new_yr = prompt_string("Publication Year", default=str(book.publication_year))
        new_ed = prompt_string("Edition", default=book.edition or "1st")
        new_qty = prompt_string("Total Quantity", default=str(book.quantity))
        new_shelf = prompt_string("Shelf Location", default=book.shelf_location or "General")

        if not prompt_confirmation("Save changes to this book?"):
            print_info("Update cancelled.")
            pause()
            return

        success, msg = self.book_service.update_book(
            book_id=book.id,
            title=new_title,
            author_id=int(new_aid) if new_aid.isdigit() else book.author_id,
            category_id=int(new_cid) if new_cid.isdigit() else book.category_id,
            publisher_id=int(new_pid) if new_pid.isdigit() else book.publisher_id,
            publication_year=int(new_yr) if new_yr.isdigit() else book.publication_year,
            edition=new_ed,
            new_quantity=int(new_qty) if new_qty.isdigit() else book.quantity,
            shelf_location=new_shelf
        )

        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def _delete_book(self) -> None:
        clear_screen()
        print_banner("DELETE BOOK")
        book_id_str = prompt_string("Enter Book ID to delete")
        if not book_id_str.isdigit():
            print_error("Invalid Book ID.")
            pause()
            return

        book = self.book_service.get_book_by_id(int(book_id_str))
        if not book:
            print_error(f"Book with ID {book_id_str} not found.")
            pause()
            return

        print_warning(f"You are about to delete: '{book.title}' [ISBN: {book.isbn}].")
        if not prompt_confirmation("Are you sure you want to delete this book?"):
            print_info("Deletion cancelled.")
            pause()
            return

        success, msg = self.book_service.delete_book(book.id)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 3. AUTHOR MANAGEMENT
    # =========================================================================
    def manage_authors(self) -> None:
        while True:
            clear_screen()
            print_banner("AUTHOR MANAGEMENT")
            print("1. Add Author")
            print("2. View All Authors")
            print("3. Search Authors")
            print("4. Update Author")
            print("5. Delete Author")
            print("6. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                name = prompt_string("Author Name")
                bio = prompt_string("Biography / Notes", required=False, default="")
                success, msg, author = self.book_service.add_author(name, bio)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
                pause()
            elif choice == "2":
                authors = self.book_service.get_all_authors()
                headers = ["ID", "Name", "Biography", "Created At"]
                rows = [[a.id, a.name, a.biography, format_date(a.created_at)] for a in authors]
                print_table(headers, rows, "No authors registered.")
                pause()
            elif choice == "3":
                q = prompt_string("Enter author search term")
                authors = self.book_service.search_authors(q)
                headers = ["ID", "Name", "Biography", "Created At"]
                rows = [[a.id, a.name, a.biography, format_date(a.created_at)] for a in authors]
                print_table(headers, rows, f"No authors found matching '{q}'.")
                pause()
            elif choice == "4":
                aid = prompt_string("Enter Author ID to update")
                if aid.isdigit():
                    author = self.book_service.get_author_by_id(int(aid))
                    if author:
                        new_name = prompt_string("Author Name", default=author.name)
                        new_bio = prompt_string("Biography", required=False, default=author.biography)
                        success, msg = self.book_service.update_author(author.id, new_name, new_bio)
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                    else:
                        print_error("Author not found.")
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "5":
                aid = prompt_string("Enter Author ID to delete")
                if aid.isdigit():
                    if prompt_confirmation("Are you sure you want to delete this author?"):
                        success, msg = self.book_service.delete_author(int(aid))
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "6":
                break
            else:
                print_error("Invalid choice.")
                pause()

    # =========================================================================
    # 4. CATEGORY MANAGEMENT
    # =========================================================================
    def manage_categories(self) -> None:
        while True:
            clear_screen()
            print_banner("CATEGORY MANAGEMENT")
            print("1. Add Category")
            print("2. View All Categories")
            print("3. Update Category")
            print("4. Delete Category")
            print("5. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                name = prompt_string("Category Name")
                desc = prompt_string("Description", required=False, default="")
                success, msg, cat = self.book_service.add_category(name, desc)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
                pause()
            elif choice == "2":
                cats = self.book_service.get_all_categories()
                headers = ["ID", "Category Name", "Description", "Created At"]
                rows = [[c.id, c.name, c.description, format_date(c.created_at)] for c in cats]
                print_table(headers, rows, "No categories registered.")
                pause()
            elif choice == "3":
                cid = prompt_string("Enter Category ID to update")
                if cid.isdigit():
                    cat = self.book_service.get_category_by_id(int(cid))
                    if cat:
                        new_name = prompt_string("Category Name", default=cat.name)
                        new_desc = prompt_string("Description", required=False, default=cat.description)
                        success, msg = self.book_service.update_category(cat.id, new_name, new_desc)
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                    else:
                        print_error("Category not found.")
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "4":
                cid = prompt_string("Enter Category ID to delete")
                if cid.isdigit():
                    if prompt_confirmation("Are you sure you want to delete this category?"):
                        success, msg = self.book_service.delete_category(int(cid))
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "5":
                break
            else:
                print_error("Invalid choice.")
                pause()

    # =========================================================================
    # 5. PUBLISHER MANAGEMENT
    # =========================================================================
    def manage_publishers(self) -> None:
        while True:
            clear_screen()
            print_banner("PUBLISHER MANAGEMENT")
            print("1. Add Publisher")
            print("2. View All Publishers")
            print("3. Search Publishers")
            print("4. Update Publisher")
            print("5. Delete Publisher")
            print("6. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                name = prompt_string("Publisher Name")
                contact = prompt_string("Contact Phone", required=False, default="")
                email = prompt_string("Email Address", required=False, default="")
                address = prompt_string("Office Address", required=False, default="")
                success, msg, pub = self.book_service.add_publisher(name, contact, email, address)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
                pause()
            elif choice == "2":
                pubs = self.book_service.get_all_publishers()
                headers = ["ID", "Name", "Contact", "Email", "Address"]
                rows = [[p.id, p.name, p.contact, p.email, p.address] for p in pubs]
                print_table(headers, rows, "No publishers registered.")
                pause()
            elif choice == "3":
                q = prompt_string("Enter publisher search term")
                pubs = self.book_service.search_publishers(q)
                headers = ["ID", "Name", "Contact", "Email", "Address"]
                rows = [[p.id, p.name, p.contact, p.email, p.address] for p in pubs]
                print_table(headers, rows, f"No publishers matching '{q}'.")
                pause()
            elif choice == "4":
                pid = prompt_string("Enter Publisher ID to update")
                if pid.isdigit():
                    pub = self.book_service.get_publisher_by_id(int(pid))
                    if pub:
                        new_name = prompt_string("Publisher Name", default=pub.name)
                        new_contact = prompt_string("Contact", required=False, default=pub.contact)
                        new_email = prompt_string("Email", required=False, default=pub.email)
                        new_addr = prompt_string("Address", required=False, default=pub.address)
                        success, msg = self.book_service.update_publisher(pub.id, new_name, new_contact, new_email, new_addr)
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                    else:
                        print_error("Publisher not found.")
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "5":
                pid = prompt_string("Enter Publisher ID to delete")
                if pid.isdigit():
                    if prompt_confirmation("Are you sure you want to delete this publisher?"):
                        success, msg = self.book_service.delete_publisher(int(pid))
                        if success:
                            print_success(msg)
                        else:
                            print_error(msg)
                else:
                    print_error("Invalid ID.")
                pause()
            elif choice == "6":
                break
            else:
                print_error("Invalid choice.")
                pause()

    # =========================================================================
    # 6. MEMBER MANAGEMENT
    # =========================================================================
    def manage_members(self) -> None:
        while True:
            clear_screen()
            print_banner("MEMBER MANAGEMENT")
            print("1. Add New Member")
            print("2. View All Members")
            print("3. Search Members")
            print("4. Update Member Details")
            print("5. Block Member Account")
            print("6. Unblock Member Account")
            print("7. Delete Member Account")
            print("8. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                self._add_member()
            elif choice == "2":
                self._view_all_members()
            elif choice == "3":
                self._search_members()
            elif choice == "4":
                self._update_member()
            elif choice == "5":
                self._block_member()
            elif choice == "6":
                self._unblock_member()
            elif choice == "7":
                self._delete_member()
            elif choice == "8":
                break
            else:
                print_error("Invalid choice.")
                pause()

    def _add_member(self) -> None:
        clear_screen()
        print_banner("REGISTER NEW MEMBER")
        full_name = prompt_string("Full Name")
        member_id = prompt_string("Member ID / Student Roll No (e.g. MEM-1005)")
        cnic = prompt_string("CNIC (XXXXX-XXXXXXX-X) or Student ID")
        phone = prompt_string("Phone Number (e.g. 0300-1234567)")
        email = prompt_string("Email Address")
        address = prompt_string("Residential Address")
        username = prompt_string("Username")
        password = prompt_string("Initial Password")
        confirm_pwd = prompt_string("Confirm Password")

        success, msg, member = self.auth_service.register_member(
            full_name=full_name,
            member_id=member_id,
            cnic=cnic,
            phone=phone,
            email=email,
            address=address,
            username=username,
            password=password,
            confirm_password=confirm_pwd
        )
        if success:
            print_success(msg)
            print_key_value_card("MEMBER ACCOUNT DETAILS", member.to_dict())
        else:
            print_error(msg)
        pause()

    def _view_all_members(self) -> None:
        clear_screen()
        print_banner("REGISTERED MEMBERS DIRECTORY")
        members = self.member_service.get_all_members()
        headers = ["ID", "Member ID", "Full Name", "CNIC", "Phone", "Email", "Status", "Joined"]
        rows = [
            [m.id, m.member_id, m.full_name, m.cnic, m.phone, m.email, m.status, format_date(m.created_at)]
            for m in members
        ]
        print_table(headers, rows, "No members found.")
        pause()

    def _search_members(self) -> None:
        clear_screen()
        print_banner("SEARCH MEMBERS")
        query = prompt_string("Enter search term (ID, Name, CNIC, Phone, Username)")
        members = self.member_service.search_members(query)
        headers = ["ID", "Member ID", "Full Name", "CNIC", "Phone", "Email", "Status", "Joined"]
        rows = [
            [m.id, m.member_id, m.full_name, m.cnic, m.phone, m.email, m.status, format_date(m.created_at)]
            for m in members
        ]
        print_table(headers, rows, f"No members found matching '{query}'.")
        pause()

    def _update_member(self) -> None:
        clear_screen()
        print_banner("UPDATE MEMBER PROFILE")
        mid_str = prompt_string("Enter Member DB ID or Member ID Code")
        member = self.member_service.get_member_by_code(mid_str) or (
            self.member_service.get_member_by_id(int(mid_str)) if mid_str.isdigit() else None
        )
        if not member:
            print_error(f"Member '{mid_str}' not found.")
            pause()
            return

        print(f"\nEditing Member: {BOLD}{member.full_name}{RESET} ({member.member_id})")
        new_name = prompt_string("Full Name", default=member.full_name)
        new_phone = prompt_string("Phone", default=member.phone)
        new_email = prompt_string("Email", default=member.email)
        new_addr = prompt_string("Address", default=member.address)

        if not prompt_confirmation("Save changes to member?"):
            print_info("Update cancelled.")
            pause()
            return

        success, msg = self.member_service.update_profile(
            member_id_num=member.id,
            full_name=new_name,
            phone=new_phone,
            email=new_email,
            address=new_addr
        )
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def _block_member(self) -> None:
        clear_screen()
        print_banner("BLOCK MEMBER ACCOUNT")
        mid_str = prompt_string("Enter Member DB ID or Member ID Code to block")
        member = self.member_service.get_member_by_code(mid_str) or (
            self.member_service.get_member_by_id(int(mid_str)) if mid_str.isdigit() else None
        )
        if not member:
            print_error(f"Member '{mid_str}' not found.")
            pause()
            return

        print_warning(f"Blocking member '{member.full_name}' will prevent them from logging in, borrowing, or renewing books.")
        if prompt_confirmation("Are you sure you want to block this member?"):
            success, msg = self.member_service.block_member(member.id)
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _unblock_member(self) -> None:
        clear_screen()
        print_banner("UNBLOCK MEMBER ACCOUNT")
        mid_str = prompt_string("Enter Member DB ID or Member ID Code to unblock")
        member = self.member_service.get_member_by_code(mid_str) or (
            self.member_service.get_member_by_id(int(mid_str)) if mid_str.isdigit() else None
        )
        if not member:
            print_error(f"Member '{mid_str}' not found.")
            pause()
            return

        if prompt_confirmation("Confirm unblocking this member account?"):
            success, msg = self.member_service.unblock_member(member.id)
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _delete_member(self) -> None:
        clear_screen()
        print_banner("DELETE MEMBER ACCOUNT")
        mid_str = prompt_string("Enter Member DB ID or Member ID Code to delete")
        member = self.member_service.get_member_by_code(mid_str) or (
            self.member_service.get_member_by_id(int(mid_str)) if mid_str.isdigit() else None
        )
        if not member:
            print_error(f"Member '{mid_str}' not found.")
            pause()
            return

        print_warning(f"Deleting member account: {member.full_name} ({member.member_id})")
        if prompt_confirmation("Are you sure you want to permanently delete this member?"):
            success, msg = self.member_service.delete_member(member.id)
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    # =========================================================================
    # 7. ISSUE BOOK FLOW
    # =========================================================================
    def issue_book_flow(self) -> None:
        clear_screen()
        print_banner("ISSUE BOOK TO MEMBER")
        member_id = prompt_string("Enter Member ID or Username")
        isbn = prompt_string("Enter Book ISBN or Book ID")

        if not prompt_confirmation("Confirm book issue transaction?"):
            print_info("Operation cancelled.")
            pause()
            return

        success, msg, borrowing = self.borrowing_service.issue_book(member_id, isbn)
        if success:
            print_success(msg)
            receipt = {
                "Borrowing ID": borrowing.borrowing_id,
                "Book Title": borrowing.book_title,
                "Book ISBN": borrowing.book_isbn,
                "Issued To": f"{borrowing.member_name} ({borrowing.member_code})",
                "Issue Date": format_date(borrowing.issue_date),
                "Due Date": format_date(borrowing.due_date),
                "Status": borrowing.status
            }
            print_key_value_card("CIRCULATION ISSUE RECEIPT", receipt)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 8. RETURN BOOK FLOW
    # =========================================================================
    def return_book_flow(self) -> None:
        clear_screen()
        print_banner("PROCESS BOOK RETURN")
        borrowing_code = prompt_string("Enter Borrowing ID (e.g. BRW202608010001)")

        borrowing = self.borrowing_service.get_borrowing_by_code(borrowing_code)
        if not borrowing:
            print_error(f"Borrowing record '{borrowing_code}' not found.")
            pause()
            return

        if borrowing.status == "Returned":
            print_warning(f"This record was already returned on {format_date(borrowing.return_date)}.")
            pause()
            return

        # Pre-calculate details for confirmation
        overdue_days = borrowing.calculate_overdue_days()
        fine_preview = Decimal(overdue_days) * Decimal("20.00")

        print(f"\nBook Title   : {BOLD}{borrowing.book_title}{RESET}")
        print(f"Member       : {borrowing.member_name} ({borrowing.member_code})")
        print(f"Issue Date   : {format_date(borrowing.issue_date)}")
        print(f"Due Date     : {format_date(borrowing.due_date)}")
        print(f"Days Overdue : {BOLD}{overdue_days}{RESET}")
        if overdue_days > 0:
            print(f"Fine Incurred: {BOLD}{format_currency(fine_preview)}{RESET}\n")
        else:
            print(f"Fine Incurred: Rs. 0.00 (On Time)\n")

        if not prompt_confirmation("Confirm book return?"):
            print_info("Return cancelled.")
            pause()
            return

        success, msg, summary = self.borrowing_service.return_book(borrowing_code)
        if success:
            print_success(msg)
            return_card = {
                "Borrowing ID": summary["borrowing_id"],
                "Book": summary["book_title"],
                "Member": summary["member_name"],
                "Return Date": format_date(summary["return_date"]),
                "Days Overdue": summary["overdue_days"],
                "Fine Generated": format_currency(summary["fine_amount"])
            }
            print_key_value_card("RETURN RECEIPT", return_card)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 9. RENEW BOOK FLOW
    # =========================================================================
    def renew_book_flow(self) -> None:
        clear_screen()
        print_banner("RENEW BORROWED BOOK")
        borrowing_code = prompt_string("Enter Borrowing ID to renew")

        if not prompt_confirmation("Confirm extension of due date?"):
            print_info("Renewal cancelled.")
            pause()
            return

        success, msg, updated_b = self.borrowing_service.renew_book(borrowing_code)
        if success:
            print_success(msg)
            card = {
                "Borrowing ID": updated_b.borrowing_id,
                "Book Title": updated_b.book_title,
                "Member": f"{updated_b.member_name} ({updated_b.member_code})",
                "New Due Date": format_date(updated_b.due_date),
                "Renewals Used": f"{updated_b.renewal_count} / 2"
            }
            print_key_value_card("RENEWAL CONFIRMATION", card)
        else:
            print_error(msg)
        pause()

    # =========================================================================
    # 10. ISSUED BOOKS
    # =========================================================================
    def view_issued_books(self) -> None:
        clear_screen()
        print_banner("CURRENTLY ISSUED BOOKS")
        issued = self.borrowing_service.get_issued_books()
        headers = ["Borrowing ID", "Member", "Book Title", "ISBN", "Issue Date", "Due Date", "Renewals"]
        rows = [
            [b.borrowing_id, f"{b.member_name} ({b.member_code})", b.book_title, b.book_isbn, format_date(b.issue_date), format_date(b.due_date), b.renewal_count]
            for b in issued
        ]
        print_table(headers, rows, "No books are currently issued.")
        pause()

    # =========================================================================
    # 11. OVERDUE BOOKS
    # =========================================================================
    def view_overdue_books(self) -> None:
        clear_screen()
        print_banner("OVERDUE BORROWINGS MONITOR")
        overdues = self.borrowing_service.get_overdue_books()
        headers = ["Borrowing ID", "Member", "Book Title", "Due Date", "Days Overdue", "Est. Fine"]
        rows = [
            [
                item["borrowing"].borrowing_id,
                f"{item['borrowing'].member_name} ({item['borrowing'].member_code})",
                item["borrowing"].book_title,
                format_date(item["borrowing"].due_date),
                f"{item['days_overdue']} day(s)",
                format_currency(item["estimated_fine"])
            ]
            for item in overdues
        ]
        print_table(headers, rows, "No overdue books! All active borrowings are within their due dates.")
        pause()

    # =========================================================================
    # 12. RESERVATIONS
    # =========================================================================
    def manage_reservations(self) -> None:
        while True:
            clear_screen()
            print_banner("RESERVATION MANAGEMENT")
            print("1. View Pending Reservations")
            print("2. Fulfill Reservation")
            print("3. Cancel Reservation")
            print("4. View All Reservations (History)")
            print("5. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                pending = self.reservation_service.get_pending_reservations()
                headers = ["Reservation ID", "Member", "Book Title", "ISBN", "Reserved On", "Stock Avail", "Status"]
                rows = [
                    [r.reservation_id, f"{r.member_name} ({r.member_code})", r.book_title, r.book_isbn, format_date(r.reservation_date), r.available_quantity, r.status]
                    for r in pending
                ]
                print_table(headers, rows, "No pending reservations.")
                pause()
            elif choice == "2":
                res_code = prompt_string("Enter Reservation ID to fulfill")
                if prompt_confirmation(f"Mark reservation '{res_code}' as FULFILLED?"):
                    success, msg = self.reservation_service.fulfill_reservation(res_code)
                    if success:
                        print_success(msg)
                    else:
                        print_error(msg)
                pause()
            elif choice == "3":
                res_code = prompt_string("Enter Reservation ID to cancel")
                if prompt_confirmation(f"Are you sure you want to CANCEL reservation '{res_code}'?"):
                    success, msg = self.reservation_service.cancel_reservation(res_code)
                    if success:
                        print_success(msg)
                    else:
                        print_error(msg)
                pause()
            elif choice == "4":
                all_res = self.reservation_service.get_all_reservations()
                headers = ["Reservation ID", "Member", "Book Title", "ISBN", "Reserved On", "Status"]
                rows = [
                    [r.reservation_id, f"{r.member_name} ({r.member_code})", r.book_title, r.book_isbn, format_date(r.reservation_date), r.status]
                    for r in all_res
                ]
                print_table(headers, rows, "No reservations found.")
                pause()
            elif choice == "5":
                break
            else:
                print_error("Invalid choice.")
                pause()

    # =========================================================================
    # 13. FINES MANAGEMENT
    # =========================================================================
    def manage_fines(self) -> None:
        while True:
            clear_screen()
            print_banner("FINE & PENALTY MANAGEMENT")
            stats = self.fine_service.get_fine_statistics()
            print(f"Total Incurred: {format_currency(stats['total_fines_amount'])} | Paid: {format_currency(stats['paid_fines_amount'])} | Unpaid Outstanding: {format_currency(stats['unpaid_fines_amount'])}\n")
            
            print("1. Mark Fine as Paid")
            print("2. View Unpaid Fines")
            print("3. View Paid Fines")
            print("4. View All Fines History")
            print("5. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                fid_str = prompt_string("Enter Fine ID to mark as paid")
                if fid_str.isdigit():
                    fine = self.fine_service.get_fine_by_id(int(fid_str))
                    if fine:
                        print(f"\nFine ID : {fine.id}")
                        print(f"Member  : {fine.member_name} ({fine.member_code})")
                        print(f"Amount  : {format_currency(fine.amount)}")
                        print(f"Reason  : {fine.reason}")
                        print(f"Status  : {fine.status}\n")

                        if prompt_confirmation("Confirm payment received?"):
                            success, msg = self.fine_service.mark_fine_as_paid(fine.id)
                            if success:
                                print_success(msg)
                            else:
                                print_error(msg)
                    else:
                        print_error("Fine record not found.")
                else:
                    print_error("Invalid Fine ID.")
                pause()
            elif choice == "2":
                unpaid = self.fine_service.get_all_fines(status="Unpaid")
                headers = ["Fine ID", "Borrowing ID", "Member", "Book", "Amount", "Reason", "Status", "Date"]
                rows = [
                    [f.id, f.borrowing_code or "-", f"{f.member_name} ({f.member_code})", f.book_title or "-", format_currency(f.amount), f.reason, f.status, format_date(f.created_at)]
                    for f in unpaid
                ]
                print_table(headers, rows, "No unpaid fines found.")
                pause()
            elif choice == "3":
                paid = self.fine_service.get_all_fines(status="Paid")
                headers = ["Fine ID", "Borrowing ID", "Member", "Amount", "Reason", "Status", "Paid At"]
                rows = [
                    [f.id, f.borrowing_code or "-", f"{f.member_name} ({f.member_code})", format_currency(f.amount), f.reason, f.status, format_date(f.paid_at)]
                    for f in paid
                ]
                print_table(headers, rows, "No paid fine records found.")
                pause()
            elif choice == "4":
                all_fines = self.fine_service.get_all_fines()
                headers = ["Fine ID", "Borrowing ID", "Member", "Amount", "Reason", "Status", "Created", "Paid At"]
                rows = [
                    [f.id, f.borrowing_code or "-", f"{f.member_name} ({f.member_code})", format_currency(f.amount), f.reason, f.status, format_date(f.created_at), format_date(f.paid_at) if f.paid_at else "-"]
                    for f in all_fines
                ]
                print_table(headers, rows, "No fine records found.")
                pause()
            elif choice == "5":
                break
            else:
                print_error("Invalid choice.")
                pause()

    # =========================================================================
    # 14. BORROWING HISTORY
    # =========================================================================
    def view_borrowing_history(self) -> None:
        while True:
            clear_screen()
            print_banner("BORROWING AUDIT LOG & HISTORY")
            print("1. View Complete Borrowing History")
            print("2. Search by Keyword (Member / Book / ISBN / ID)")
            print("3. Filter by Status (Issued / Returned / Overdue)")
            print("4. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                records = self.borrowing_service.search_borrowing_history()
                self._display_history_table(records)
            elif choice == "2":
                q = prompt_string("Enter search keyword")
                records = self.borrowing_service.search_borrowing_history(query=q)
                self._display_history_table(records, empty_msg=f"No borrowings matching '{q}'.")
            elif choice == "3":
                print("Filter by: 1. Issued  2. Returned  3. Overdue")
                f_choice = prompt_choice("Choose filter (1-3): ")
                status_map = {"1": "Issued", "2": "Returned", "3": "OVERDUE"}
                status = status_map.get(f_choice, "ALL")
                records = self.borrowing_service.search_borrowing_history(status_filter=status)
                self._display_history_table(records, empty_msg=f"No borrowings with status '{status}'.")
            elif choice == "4":
                break
            else:
                print_error("Invalid option.")
                pause()

    def _display_history_table(self, records: list, empty_msg: str = "No borrowing records found.") -> None:
        headers = ["Borrowing ID", "Member", "Book Title", "ISBN", "Issue Date", "Due Date", "Return Date", "Status"]
        rows = [
            [
                b.borrowing_id,
                f"{b.member_name} ({b.member_code})",
                b.book_title,
                b.book_isbn,
                format_date(b.issue_date),
                format_date(b.due_date),
                format_date(b.return_date) if b.return_date else "-",
                b.status
            ]
            for b in records
        ]
        print_table(headers, rows, empty_msg)
        pause()

    # =========================================================================
    # 15. REPORTS & CSV EXPORT
    # =========================================================================
    def manage_reports(self) -> None:
        while True:
            clear_screen()
            print_banner("REPORTS & DATA EXPORT ENGINE")
            print("1. Book Inventory Report (with CSV Export option)")
            print("2. Members Directory Report (with CSV Export option)")
            print("3. Circulation & Borrowing Report (with CSV Export option)")
            print("4. Financial & Fines Report (with CSV Export option)")
            print("5. Reservations Report (with CSV Export option)")
            print("6. Batch Export All Reports to CSV")
            print("7. Back to Admin Menu")
            print("-" * 60)

            choice = prompt_choice()
            if choice == "1":
                self._report_books()
            elif choice == "2":
                self._report_members()
            elif choice == "3":
                self._report_borrowings()
            elif choice == "4":
                self._report_fines()
            elif choice == "5":
                self._report_reservations()
            elif choice == "6":
                self._export_all_reports()
            elif choice == "7":
                break
            else:
                print_error("Invalid option.")
                pause()

    def _report_books(self) -> None:
        clear_screen()
        report = self.report_generator.get_book_report()
        print_key_value_card("BOOK INVENTORY REPORT SUMMARY", report["summary"])
        if prompt_confirmation("Export books report to CSV?"):
            success, msg, path = self.report_generator.export_books_csv()
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _report_members(self) -> None:
        clear_screen()
        report = self.report_generator.get_member_report()
        print_key_value_card("MEMBER DIRECTORY REPORT SUMMARY", report["summary"])
        if prompt_confirmation("Export members report to CSV?"):
            success, msg, path = self.report_generator.export_members_csv()
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _report_borrowings(self) -> None:
        clear_screen()
        report = self.report_generator.get_borrowing_report()
        print_key_value_card("CIRCULATION REPORT SUMMARY", report["summary"])
        if prompt_confirmation("Export borrowings report to CSV?"):
            success, msg, path = self.report_generator.export_borrowings_csv()
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _report_fines(self) -> None:
        clear_screen()
        report = self.report_generator.get_fine_report()
        formatted_summary = {
            k: format_currency(v) if isinstance(v, Decimal) else v
            for k, v in report["summary"].items()
        }
        print_key_value_card("FINANCIAL FINES REPORT SUMMARY", formatted_summary)
        if prompt_confirmation("Export fines report to CSV?"):
            success, msg, path = self.report_generator.export_fines_csv()
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _report_reservations(self) -> None:
        clear_screen()
        report = self.report_generator.get_reservation_report()
        print_key_value_card("RESERVATIONS REPORT SUMMARY", report["summary"])
        if prompt_confirmation("Export reservations report to CSV?"):
            success, msg, path = self.report_generator.export_reservations_csv()
            if success:
                print_success(msg)
            else:
                print_error(msg)
        pause()

    def _export_all_reports(self) -> None:
        clear_screen()
        print_banner("BATCH CSV EXPORT")
        print_info("Exporting all system reports to the data/ directory...")

        res_b, msg_b, _ = self.report_generator.export_books_csv()
        res_m, msg_m, _ = self.report_generator.export_members_csv()
        res_bw, msg_bw, _ = self.report_generator.export_borrowings_csv()
        res_f, msg_f, _ = self.report_generator.export_fines_csv()
        res_r, msg_r, _ = self.report_generator.export_reservations_csv()

        if all([res_b, res_m, res_bw, res_f, res_r]):
            print_success("All 5 reports exported to CSV successfully!")
            print(" - books_report.csv\n - members_report.csv\n - borrowings_report.csv\n - fines_report.csv\n - reservations_report.csv")
        else:
            print_error("Some reports encountered export errors. Check log file for details.")
        pause()
