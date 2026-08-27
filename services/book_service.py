"""
Book and Catalog Service.
Handles Books, Authors, Categories, and Publishers with relational integrity and quantity synchronization.
"""

from typing import Optional, Tuple
from database import DatabaseManager
from models.author import Author
from models.book import Book
from models.category import Category
from models.publisher import Publisher
from utils.logger import log_event
from utils.validators import validate_isbn, validate_positive_int, validate_year


class BookService:
    """
    Catalog service for Authors, Categories, Publishers, and Books.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    # =========================================================================
    # AUTHOR MANAGEMENT
    # =========================================================================
    def add_author(self, name: str, biography: str = "") -> Tuple[bool, str, Optional[Author]]:
        if not name or not name.strip():
            return False, "Author name cannot be empty.", None
        name = name.strip()

        existing = self.db.fetch_one("SELECT id FROM authors WHERE name = ? COLLATE NOCASE", (name,))
        if existing:
            return False, f"Author '{name}' already exists.", None

        try:
            aid = self.db.execute_update(
                "INSERT INTO authors (name, biography) VALUES (?, ?)",
                (name, biography.strip())
            )
            log_event("INFO", f"Author added: {name} (ID: {aid})")
            row = self.db.fetch_one("SELECT * FROM authors WHERE id = ?", (aid,))
            return True, f"Author '{name}' added successfully.", Author.from_row(row)
        except Exception as e:
            log_event("ERROR", f"Error adding author: {e}")
            return False, f"Database error adding author: {e}", None

    def get_all_authors(self) -> list[Author]:
        rows = self.db.fetch_all("SELECT * FROM authors ORDER BY name ASC")
        return [Author.from_row(r) for r in rows]

    def search_authors(self, query: str) -> list[Author]:
        term = f"%{query.strip()}%"
        rows = self.db.fetch_all(
            "SELECT * FROM authors WHERE name LIKE ? OR biography LIKE ? ORDER BY name ASC",
            (term, term)
        )
        return [Author.from_row(r) for r in rows]

    def get_author_by_id(self, author_id: int) -> Optional[Author]:
        row = self.db.fetch_one("SELECT * FROM authors WHERE id = ?", (author_id,))
        return Author.from_row(row) if row else None

    def update_author(self, author_id: int, name: str, biography: str = "") -> Tuple[bool, str]:
        if not name or not name.strip():
            return False, "Author name cannot be empty."
        name = name.strip()

        existing = self.db.fetch_one(
            "SELECT id FROM authors WHERE name = ? COLLATE NOCASE AND id != ?",
            (name, author_id)
        )
        if existing:
            return False, f"Another author with the name '{name}' already exists."

        try:
            self.db.execute_update(
                "UPDATE authors SET name = ?, biography = ? WHERE id = ?",
                (name, biography.strip(), author_id)
            )
            log_event("INFO", f"Author ID {author_id} updated to '{name}'")
            return True, "Author updated successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating author: {e}")
            return False, f"Failed to update author: {e}"

    def delete_author(self, author_id: int) -> Tuple[bool, str]:
        book_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM books WHERE author_id = ?",
            (author_id,)
        )["count"]
        if book_count > 0:
            return False, f"Cannot delete author. There are {book_count} book(s) associated with this author."

        try:
            self.db.execute_update("DELETE FROM authors WHERE id = ?", (author_id,))
            log_event("INFO", f"Author ID {author_id} deleted.")
            return True, "Author deleted successfully."
        except Exception as e:
            log_event("ERROR", f"Error deleting author: {e}")
            return False, f"Failed to delete author: {e}"

    # =========================================================================
    # CATEGORY MANAGEMENT
    # =========================================================================
    def add_category(self, name: str, description: str = "") -> Tuple[bool, str, Optional[Category]]:
        if not name or not name.strip():
            return False, "Category name cannot be empty.", None
        name = name.strip()

        existing = self.db.fetch_one("SELECT id FROM categories WHERE name = ? COLLATE NOCASE", (name,))
        if existing:
            return False, f"Category '{name}' already exists.", None

        try:
            cid = self.db.execute_update(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description.strip())
            )
            log_event("INFO", f"Category added: {name} (ID: {cid})")
            row = self.db.fetch_one("SELECT * FROM categories WHERE id = ?", (cid,))
            return True, f"Category '{name}' added successfully.", Category.from_row(row)
        except Exception as e:
            log_event("ERROR", f"Error adding category: {e}")
            return False, f"Database error adding category: {e}", None

    def get_all_categories(self) -> list[Category]:
        rows = self.db.fetch_all("SELECT * FROM categories ORDER BY name ASC")
        return [Category.from_row(r) for r in rows]

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        row = self.db.fetch_one("SELECT * FROM categories WHERE id = ?", (category_id,))
        return Category.from_row(row) if row else None

    def update_category(self, category_id: int, name: str, description: str = "") -> Tuple[bool, str]:
        if not name or not name.strip():
            return False, "Category name cannot be empty."
        name = name.strip()

        existing = self.db.fetch_one(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND id != ?",
            (name, category_id)
        )
        if existing:
            return False, f"Another category with the name '{name}' already exists."

        try:
            self.db.execute_update(
                "UPDATE categories SET name = ?, description = ? WHERE id = ?",
                (name, description.strip(), category_id)
            )
            log_event("INFO", f"Category ID {category_id} updated to '{name}'")
            return True, "Category updated successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating category: {e}")
            return False, f"Failed to update category: {e}"

    def delete_category(self, category_id: int) -> Tuple[bool, str]:
        book_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM books WHERE category_id = ?",
            (category_id,)
        )["count"]
        if book_count > 0:
            return False, f"Cannot delete category. There are {book_count} book(s) assigned to this category."

        try:
            self.db.execute_update("DELETE FROM categories WHERE id = ?", (category_id,))
            log_event("INFO", f"Category ID {category_id} deleted.")
            return True, "Category deleted successfully."
        except Exception as e:
            log_event("ERROR", f"Error deleting category: {e}")
            return False, f"Failed to delete category: {e}"

    # =========================================================================
    # PUBLISHER MANAGEMENT
    # =========================================================================
    def add_publisher(self, name: str, contact: str = "", email: str = "", address: str = "") -> Tuple[bool, str, Optional[Publisher]]:
        if not name or not name.strip():
            return False, "Publisher name cannot be empty.", None
        name = name.strip()

        existing = self.db.fetch_one("SELECT id FROM publishers WHERE name = ? COLLATE NOCASE", (name,))
        if existing:
            return False, f"Publisher '{name}' already exists.", None

        try:
            pid = self.db.execute_update(
                "INSERT INTO publishers (name, contact, email, address) VALUES (?, ?, ?, ?)",
                (name, contact.strip(), email.strip(), address.strip())
            )
            log_event("INFO", f"Publisher added: {name} (ID: {pid})")
            row = self.db.fetch_one("SELECT * FROM publishers WHERE id = ?", (pid,))
            return True, f"Publisher '{name}' added successfully.", Publisher.from_row(row)
        except Exception as e:
            log_event("ERROR", f"Error adding publisher: {e}")
            return False, f"Database error adding publisher: {e}", None

    def get_all_publishers(self) -> list[Publisher]:
        rows = self.db.fetch_all("SELECT * FROM publishers ORDER BY name ASC")
        return [Publisher.from_row(r) for r in rows]

    def search_publishers(self, query: str) -> list[Publisher]:
        term = f"%{query.strip()}%"
        rows = self.db.fetch_all(
            "SELECT * FROM publishers WHERE name LIKE ? OR contact LIKE ? OR email LIKE ? ORDER BY name ASC",
            (term, term, term)
        )
        return [Publisher.from_row(r) for r in rows]

    def get_publisher_by_id(self, publisher_id: int) -> Optional[Publisher]:
        row = self.db.fetch_one("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
        return Publisher.from_row(row) if row else None

    def update_publisher(self, publisher_id: int, name: str, contact: str = "", email: str = "", address: str = "") -> Tuple[bool, str]:
        if not name or not name.strip():
            return False, "Publisher name cannot be empty."
        name = name.strip()

        existing = self.db.fetch_one(
            "SELECT id FROM publishers WHERE name = ? COLLATE NOCASE AND id != ?",
            (name, publisher_id)
        )
        if existing:
            return False, f"Another publisher with the name '{name}' already exists."

        try:
            self.db.execute_update(
                "UPDATE publishers SET name = ?, contact = ?, email = ?, address = ? WHERE id = ?",
                (name, contact.strip(), email.strip(), address.strip(), publisher_id)
            )
            log_event("INFO", f"Publisher ID {publisher_id} updated to '{name}'")
            return True, "Publisher updated successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating publisher: {e}")
            return False, f"Failed to update publisher: {e}"

    def delete_publisher(self, publisher_id: int) -> Tuple[bool, str]:
        book_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM books WHERE publisher_id = ?",
            (publisher_id,)
        )["count"]
        if book_count > 0:
            return False, f"Cannot delete publisher. There are {book_count} book(s) published by this publisher."

        try:
            self.db.execute_update("DELETE FROM publishers WHERE id = ?", (publisher_id,))
            log_event("INFO", f"Publisher ID {publisher_id} deleted.")
            return True, "Publisher deleted successfully."
        except Exception as e:
            log_event("ERROR", f"Error deleting publisher: {e}")
            return False, f"Failed to delete publisher: {e}"

    # =========================================================================
    # BOOK MANAGEMENT
    # =========================================================================
    def _book_query_base(self) -> str:
        return """
            SELECT 
                b.*,
                a.name as author_name,
                c.name as category_name,
                p.name as publisher_name
            FROM books b
            LEFT JOIN authors a ON b.author_id = a.id
            LEFT JOIN categories c ON b.category_id = c.id
            LEFT JOIN publishers p ON b.publisher_id = p.id
        """

    def add_book(
        self,
        isbn: str,
        title: str,
        author_id: int,
        category_id: int,
        publisher_id: int,
        publication_year: int,
        edition: str,
        quantity: int,
        shelf_location: str
    ) -> Tuple[bool, str, Optional[Book]]:
        # 1. Validations
        valid_isbn, err_isbn = validate_isbn(isbn)
        if not valid_isbn:
            return False, err_isbn, None
        isbn = isbn.strip().replace("-", "").replace(" ", "")

        if not title or not title.strip():
            return False, "Book title cannot be empty.", None
        title = title.strip()

        valid_yr, err_yr = validate_year(publication_year)
        if not valid_yr:
            return False, err_yr, None

        valid_qty, err_qty, qty_int = validate_positive_int(quantity, "Quantity")
        if not valid_qty:
            return False, err_qty, None

        # 2. Check foreign references exist
        if not self.get_author_by_id(author_id):
            return False, f"Author with ID {author_id} does not exist.", None
        if not self.get_category_by_id(category_id):
            return False, f"Category with ID {category_id} does not exist.", None
        if not self.get_publisher_by_id(publisher_id):
            return False, f"Publisher with ID {publisher_id} does not exist.", None

        # 3. Check duplicate ISBN
        existing = self.db.fetch_one("SELECT id FROM books WHERE isbn = ?", (isbn,))
        if existing:
            return False, f"A book with ISBN '{isbn}' already exists in the system.", None

        # 4. Insert book
        try:
            status = "Available" if qty_int > 0 else "Unavailable"
            book_id = self.db.execute_update(
                """
                INSERT INTO books (
                    isbn, title, author_id, category_id, publisher_id,
                    publication_year, edition, quantity, available_quantity,
                    shelf_location, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    isbn, title, author_id, category_id, publisher_id,
                    int(publication_year), edition.strip() if edition else "1st",
                    qty_int, qty_int, shelf_location.strip() if shelf_location else "General",
                    status
                )
            )
            log_event("INFO", f"New book added: '{title}' [ISBN: {isbn}] (ID: {book_id})")
            
            row = self.db.fetch_one(f"{self._book_query_base()} WHERE b.id = ?", (book_id,))
            return True, f"Book '{title}' added successfully.", Book.from_row(row)
        except Exception as e:
            log_event("ERROR", f"Error adding book: {e}")
            return False, f"Failed to add book: {e}", None

    def get_all_books(self) -> list[Book]:
        rows = self.db.fetch_all(f"{self._book_query_base()} ORDER BY b.title ASC")
        return [Book.from_row(r) for r in rows]

    def get_available_books(self) -> list[Book]:
        rows = self.db.fetch_all(f"{self._book_query_base()} WHERE b.available_quantity > 0 ORDER BY b.title ASC")
        return [Book.from_row(r) for r in rows]

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        row = self.db.fetch_one(f"{self._book_query_base()} WHERE b.id = ?", (book_id,))
        return Book.from_row(row) if row else None

    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        clean_isbn = isbn.strip().replace("-", "").replace(" ", "")
        row = self.db.fetch_one(f"{self._book_query_base()} WHERE b.isbn = ?", (clean_isbn,))
        return Book.from_row(row) if row else None

    def search_books(self, query: str) -> list[Book]:
        """
        Search books across ISBN, Title, Author, Category, Publisher, or Shelf.
        """
        term = f"%{query.strip()}%"
        clean_isbn_term = f"%{query.strip().replace('-', '').replace(' ', '')}%"
        sql = f"""
            {self._book_query_base()}
            WHERE b.isbn LIKE ?
               OR b.title LIKE ?
               OR a.name LIKE ?
               OR c.name LIKE ?
               OR p.name LIKE ?
               OR b.shelf_location LIKE ?
            ORDER BY b.title ASC
        """
        rows = self.db.fetch_all(sql, (clean_isbn_term, term, term, term, term, term))
        return [Book.from_row(r) for r in rows]

    def update_book(
        self,
        book_id: int,
        title: str,
        author_id: int,
        category_id: int,
        publisher_id: int,
        publication_year: int,
        edition: str,
        new_quantity: int,
        shelf_location: str
    ) -> Tuple[bool, str]:
        # Validate book exists
        current_book = self.get_book_by_id(book_id)
        if not current_book:
            return False, "Book not found."

        if not title or not title.strip():
            return False, "Book title cannot be empty."

        valid_yr, err_yr = validate_year(publication_year)
        if not valid_yr:
            return False, err_yr

        valid_qty, err_qty, qty_int = validate_positive_int(new_quantity, "Quantity")
        if not valid_qty:
            return False, err_qty

        # Verify foreign references
        if not self.get_author_by_id(author_id):
            return False, f"Author ID {author_id} not found."
        if not self.get_category_by_id(category_id):
            return False, f"Category ID {category_id} not found."
        if not self.get_publisher_by_id(publisher_id):
            return False, f"Publisher ID {publisher_id} not found."

        # Consistency Check: Calculate currently issued copies
        currently_issued = current_book.quantity - current_book.available_quantity
        if qty_int < currently_issued:
            return (
                False,
                f"Cannot reduce quantity to {qty_int}. There are currently {currently_issued} copies issued to members."
            )

        new_available = qty_int - currently_issued
        status = "Available" if new_available > 0 else "Unavailable"

        try:
            self.db.execute_update(
                """
                UPDATE books SET
                    title = ?,
                    author_id = ?,
                    category_id = ?,
                    publisher_id = ?,
                    publication_year = ?,
                    edition = ?,
                    quantity = ?,
                    available_quantity = ?,
                    shelf_location = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    title.strip(), author_id, category_id, publisher_id,
                    int(publication_year), edition.strip() if edition else "1st",
                    qty_int, new_available, shelf_location.strip() if shelf_location else "General",
                    status, book_id
                )
            )
            log_event("INFO", f"Book ID {book_id} ('{title}') updated. Qty: {qty_int}, Avail: {new_available}")
            return True, "Book details updated successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating book: {e}")
            return False, f"Failed to update book: {e}"

    def delete_book(self, book_id: int) -> Tuple[bool, str]:
        current_book = self.get_book_by_id(book_id)
        if not current_book:
            return False, "Book not found."

        # Check for active borrowings
        active_borrowings = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM borrowings WHERE book_id = ? AND status = 'Issued'",
            (book_id,)
        )["count"]

        if active_borrowings > 0:
            return False, f"Cannot delete book. There are currently {active_borrowings} active borrowing(s) for this book."

        try:
            with self.db.transaction() as conn:
                # Cancel any pending reservations
                conn.execute(
                    "UPDATE reservations SET status = 'Cancelled' WHERE book_id = ? AND status = 'Pending'",
                    (book_id,)
                )
                conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            
            log_event("INFO", f"Book ID {book_id} ('{current_book.title}') deleted.")
            return True, f"Book '{current_book.title}' deleted successfully."
        except Exception as e:
            log_event("ERROR", f"Error deleting book ID {book_id}: {e}")
            return False, f"Failed to delete book: {e}"
