"""
Database Management Module.
Handles SQLite3 connections, schema initialization, foreign key constraints,
transaction safety, and parameterized queries.
"""

from contextlib import contextmanager
import sqlite3
import threading
from typing import Any, Generator, Optional
from config import DB_NAME
from utils.logger import log_event


class DatabaseManager:
    """
    Thread-safe SQLite Database Manager for Library Management System.
    """
    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = DB_NAME) -> "DatabaseManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = DB_NAME):
        if self._initialized:
            return
        self.db_path = db_path
        self._local = threading.local()
        self._initialized = True
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get or create a thread-local SQLite database connection.
        Enables foreign keys and returns Row objects.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.connection = conn
        return self._local.connection

    def close(self) -> None:
        """Close the current thread's connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
            except Exception as e:
                log_event("WARNING", f"Error closing database connection: {e}")
            finally:
                self._local.connection = None

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for safe atomic transactions.
        Commits on success, rolls back on any exception.
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as err:
            conn.rollback()
            log_event("ERROR", f"Transaction rolled back due to error: {err}")
            raise err

    def execute_query(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query without committing automatically."""
        conn = self.get_connection()
        return conn.execute(sql, params)

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query and commit immediately.
        Returns lastrowid for INSERT or rowcount for UPDATE/DELETE.
        """
        with self.transaction() as conn:
            cursor = conn.execute(sql, params)
            if sql.strip().upper().startswith("INSERT"):
                return cursor.lastrowid
            return cursor.rowcount

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch a single row."""
        conn = self.get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchone()

    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Fetch all matching rows."""
        conn = self.get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

    def initialize_database(self) -> None:
        """
        Create all required tables, triggers, and indices if they do not exist.
        """
        with self.transaction() as conn:
            # 1. Admins Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Members Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    cnic TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    address TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Blocked')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Authors Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    biography TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Categories Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 5. Publishers Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS publishers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    contact TEXT,
                    email TEXT,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 6. Books Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE RESTRICT,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                    publisher_id INTEGER NOT NULL REFERENCES publishers(id) ON DELETE RESTRICT,
                    publication_year INTEGER NOT NULL,
                    edition TEXT,
                    quantity INTEGER NOT NULL CHECK(quantity >= 0),
                    available_quantity INTEGER NOT NULL CHECK(available_quantity >= 0 AND available_quantity <= quantity),
                    shelf_location TEXT,
                    status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Unavailable')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 7. Borrowings Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS borrowings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    borrowing_id TEXT UNIQUE NOT NULL,
                    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
                    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    return_date TEXT,
                    renewal_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Issued' CHECK(status IN ('Issued', 'Returned', 'Overdue')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 8. Fines Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    borrowing_id INTEGER REFERENCES borrowings(id) ON DELETE SET NULL,
                    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(status IN ('Unpaid', 'Paid')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TEXT
                );
            """)

            # 9. Reservations Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reservation_id TEXT UNIQUE NOT NULL,
                    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
                    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
                    reservation_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Fulfilled', 'Cancelled')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create Helpful Indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_members_id ON members(member_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_members_user ON members(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_borrowings_status ON borrowings(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_borrowings_member ON borrowings(member_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fines_member ON fines(member_id, status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reservations_book ON reservations(book_id, status);")

        log_event("INFO", "Database schema initialized successfully.")
