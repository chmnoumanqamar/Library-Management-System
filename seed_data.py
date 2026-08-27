"""
Database Seed & Demo Data Loader.
Populates sample administrators, authors, categories, publishers, books, and members
for initial demonstration, testing, and viva evaluation.
"""

import datetime
from decimal import Decimal
from database import DatabaseManager
from utils.logger import log_event
from utils.security import hash_password


def seed_database(force: bool = False) -> None:
    """
    Seed initial data into database if empty or force=True.
    """
    db = DatabaseManager()

    admin_count = db.fetch_one("SELECT COUNT(*) as count FROM admins")["count"]
    if admin_count > 0 and not force:
        return

    log_event("INFO", "Starting database demo data seeding...")

    with db.transaction() as conn:
        # 1. Seed Admin
        admin_pwd_hash, admin_salt = hash_password("admin123")
        conn.execute(
            """
            INSERT OR IGNORE INTO admins (username, password_hash, salt, full_name, email)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("admin", admin_pwd_hash, admin_salt, "Chief Librarian", "admin@library.edu")
        )

        # 2. Seed Authors
        authors_data = [
            ("Robert C. Martin", "Legendary software craftsmanship advocate, author of Clean Code and Clean Architecture."),
            ("Eric Matthes", "Educator and author of the best-selling Python Crash Course."),
            ("Al Sweigart", "Software developer and creative author of practical Python automation literature."),
            ("Martin Fowler", "Chief Scientist at ThoughtWorks, international speaker on enterprise software architecture."),
            ("Andrew Hunt", "Pioneer and co-author of The Pragmatic Programmer and Agile Manifesto signatory."),
            ("Ian Goodfellow", "Distinguished AI researcher, inventor of Generative Adversarial Networks (GANs).")
        ]
        author_ids = {}
        for name, bio in authors_data:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO authors (name, biography) VALUES (?, ?)",
                (name, bio)
            )
            aid = cursor.lastrowid
            if not aid:
                aid = conn.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()[0]
            author_ids[name] = aid

        # 3. Seed Categories
        categories_data = [
            ("Programming", "Core syntax, algorithms, and practical programming languages."),
            ("Software Engineering", "Design patterns, refactoring, testing, and clean architecture."),
            ("Artificial Intelligence", "Machine learning, neural networks, and modern AI algorithms."),
            ("Computer Science", "Fundamental theories, data structures, and operating systems."),
            ("Mathematics", "Discrete structures, linear algebra, and mathematical statistics."),
            ("Literature", "Classic and contemporary literary masterpieces and fiction.")
        ]
        category_ids = {}
        for name, desc in categories_data:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
                (name, desc)
            )
            cid = cursor.lastrowid
            if not cid:
                cid = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()[0]
            category_ids[name] = cid

        # 4. Seed Publishers
        publishers_data = [
            ("Prentice Hall", "+1-201-555-0100", "contact@prenticehall.com", "Upper Saddle River, NJ"),
            ("No Starch Press", "+1-415-555-0199", "info@nostarch.com", "San Francisco, CA"),
            ("Addison-Wesley", "+1-617-555-0122", "info@aw.com", "Boston, MA"),
            ("MIT Press", "+1-617-555-0144", "mitpress@mit.edu", "Cambridge, MA"),
            ("O'Reilly Media", "+1-707-555-0155", "support@oreilly.com", "Sebastopol, CA")
        ]
        publisher_ids = {}
        for name, contact, email, address in publishers_data:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO publishers (name, contact, email, address) VALUES (?, ?, ?, ?)",
                (name, contact, email, address)
            )
            pid = cursor.lastrowid
            if not pid:
                pid = conn.execute("SELECT id FROM publishers WHERE name = ?", (name,)).fetchone()[0]
            publisher_ids[name] = pid

        # 5. Seed Books
        books_data = [
            (
                "9780132350884", "Clean Code: A Handbook of Agile Software Craftsmanship",
                author_ids["Robert C. Martin"], category_ids["Software Engineering"], publisher_ids["Prentice Hall"],
                2008, "1st", 5, 4, "SE-101", "Available"
            ),
            (
                "9781593279288", "Python Crash Course: A Hands-On, Project-Based Introduction",
                author_ids["Eric Matthes"], category_ids["Programming"], publisher_ids["No Starch Press"],
                2019, "2nd", 4, 3, "PRG-204", "Available"
            ),
            (
                "9781593279929", "Automate the Boring Stuff with Python",
                author_ids["Al Sweigart"], category_ids["Programming"], publisher_ids["No Starch Press"],
                2019, "2nd", 3, 3, "PRG-205", "Available"
            ),
            (
                "9780201485677", "Refactoring: Improving the Design of Existing Code",
                author_ids["Martin Fowler"], category_ids["Software Engineering"], publisher_ids["Addison-Wesley"],
                2018, "2nd", 4, 4, "SE-102", "Available"
            ),
            (
                "9780135957059", "The Pragmatic Programmer: Your Journey To Mastery",
                author_ids["Andrew Hunt"], category_ids["Software Engineering"], publisher_ids["Addison-Wesley"],
                2019, "20th Anniversary", 3, 3, "SE-103", "Available"
            ),
            (
                "9780262035613", "Deep Learning",
                author_ids["Ian Goodfellow"], category_ids["Artificial Intelligence"], publisher_ids["MIT Press"],
                2016, "1st", 2, 2, "AI-301", "Available"
            )
        ]
        book_ids = {}
        for isbn, title, aid, cid, pid, year, edition, qty, avail, shelf, status in books_data:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO books (
                    isbn, title, author_id, category_id, publisher_id,
                    publication_year, edition, quantity, available_quantity,
                    shelf_location, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (isbn, title, aid, cid, pid, year, edition, qty, avail, shelf, status)
            )
            b_id = cursor.lastrowid
            if not b_id:
                b_id = conn.execute("SELECT id FROM books WHERE isbn = ?", (isbn,)).fetchone()[0]
            book_ids[isbn] = b_id

        # 6. Seed Members
        members_data = [
            (
                "MEM-1001", "Ali Khan", "35202-1234567-1", "0300-1234567",
                "ali.khan@example.com", "Gulberg III, Lahore", "alikhan", "password123", "Active"
            ),
            (
                "MEM-1002", "Sarah Ahmed", "42101-7654321-2", "0321-7654321",
                "sarah.ahmed@example.com", "DHA Phase 5, Karachi", "sarahahmed", "password123", "Active"
            ),
            (
                "MEM-1003", "Muhammad Usman", "61101-9876543-3", "0333-9876543",
                "usman.m@example.com", "F-8/2, Islamabad", "usman", "password123", "Active"
            ),
            (
                "MEM-1004", "Fatima Noor", "33100-5554443-4", "0345-5554443",
                "fatima.noor@example.com", "Satellite Town, Rawalpindi", "fatima", "password123", "Blocked"
            )
        ]
        member_ids = {}
        for mid, name, cnic, phone, email, addr, username, pwd, status in members_data:
            m_hash, m_salt = hash_password(pwd)
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO members (
                    member_id, full_name, cnic, phone, email, address, username, password_hash, salt, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mid, name, cnic, phone, email, addr, username, m_hash, m_salt, status)
            )
            m_db_id = cursor.lastrowid
            if not m_db_id:
                m_db_id = conn.execute("SELECT id FROM members WHERE member_id = ?", (mid,)).fetchone()[0]
            member_ids[mid] = m_db_id

        # 7. Seed Sample Borrowings
        today = datetime.date.today()
        
        # Borrowing 1: Ali Khan borrowed Clean Code (Active, not overdue)
        issue_1 = today - datetime.timedelta(days=4)
        due_1 = issue_1 + datetime.timedelta(days=14)
        conn.execute(
            """
            INSERT OR IGNORE INTO borrowings (
                borrowing_id, member_id, book_id, issue_date, due_date, renewal_count, status
            ) VALUES (?, ?, ?, ?, ?, 0, 'Issued')
            """,
            (
                "BRW202608010001",
                member_ids["MEM-1001"],
                book_ids["9780132350884"],
                issue_1.strftime("%Y-%m-%d"),
                due_1.strftime("%Y-%m-%d")
            )
        )

        # Borrowing 2: Sarah Ahmed borrowed Python Crash Course (Overdue by 5 days)
        issue_2 = today - datetime.timedelta(days=19)
        due_2 = issue_2 + datetime.timedelta(days=14)
        conn.execute(
            """
            INSERT OR IGNORE INTO borrowings (
                borrowing_id, member_id, book_id, issue_date, due_date, renewal_count, status
            ) VALUES (?, ?, ?, ?, ?, 0, 'Issued')
            """,
            (
                "BRW202608020002",
                member_ids["MEM-1002"],
                book_ids["9781593279288"],
                issue_2.strftime("%Y-%m-%d"),
                due_2.strftime("%Y-%m-%d")
            )
        )

        # 8. Seed Sample Fine for an older returned book
        conn.execute(
            """
            INSERT OR IGNORE INTO fines (borrowing_id, member_id, amount, reason, status, created_at)
            VALUES (?, ?, ?, ?, 'Unpaid', ?)
            """,
            (
                None,
                member_ids["MEM-1001"],
                60.00,
                "Overdue return: 3 days overdue on historical borrowing",
                (today - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        # 9. Seed Sample Reservation
        conn.execute(
            """
            INSERT OR IGNORE INTO reservations (
                reservation_id, member_id, book_id, reservation_date, status
            ) VALUES (?, ?, ?, ?, 'Pending')
            """,
            (
                "RES202608010001",
                member_ids["MEM-1003"],
                book_ids["9780262035613"],
                today.strftime("%Y-%m-%d")
            )
        )

    log_event("INFO", "Database demo data seeded successfully.")
