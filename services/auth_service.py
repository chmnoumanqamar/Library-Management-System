"""
Authentication Service.
Handles admin login, member login/registration, password hashing, and session lockout protection.
"""

import datetime
import time
from typing import Optional, Tuple
from config import LOCKOUT_DURATION_SECONDS, MAX_LOGIN_ATTEMPTS
from database import DatabaseManager
from models.admin import Admin
from models.member import Member
from utils.logger import log_event
from utils.security import hash_password, verify_password
from utils.validators import (
    validate_cnic,
    validate_email,
    validate_name,
    validate_phone,
    validate_username,
)


class AuthService:
    """
    Service layer for user authentication and credentials management.
    """
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self._failed_attempts: dict[str, int] = {}
        self._lockouts: dict[str, float] = {}

    def _check_lockout(self, identifier: str) -> Tuple[bool, int]:
        """Check if an identifier is temporarily locked out."""
        if identifier in self._lockouts:
            remaining = int(self._lockouts[identifier] - time.time())
            if remaining > 0:
                return True, remaining
            else:
                del self._lockouts[identifier]
                self._failed_attempts[identifier] = 0
        return False, 0

    def _record_failed_attempt(self, identifier: str) -> None:
        """Record a failed login attempt and apply lockout if limit reached."""
        count = self._failed_attempts.get(identifier, 0) + 1
        self._failed_attempts[identifier] = count
        if count >= MAX_LOGIN_ATTEMPTS:
            self._lockouts[identifier] = time.time() + LOCKOUT_DURATION_SECONDS
            log_event("WARNING", f"Security lockout triggered for identifier: {identifier}")

    def _reset_failed_attempts(self, identifier: str) -> None:
        """Reset failed login attempts on successful authentication."""
        self._failed_attempts.pop(identifier, None)
        self._lockouts.pop(identifier, None)

    def login_admin(self, username: str, plain_password: str) -> Tuple[bool, str, Optional[Admin]]:
        """
        Authenticate an admin user.
        """
        if not username or not plain_password:
            return False, "Username and password are required.", None

        locked, remaining = self._check_lockout(f"admin:{username}")
        if locked:
            return False, f"Too many failed login attempts. Please wait {remaining} seconds before trying again.", None

        row = self.db.fetch_one(
            "SELECT * FROM admins WHERE username = ? COLLATE NOCASE",
            (username.strip(),)
        )

        if not row:
            self._record_failed_attempt(f"admin:{username}")
            log_event("WARNING", f"Failed admin login attempt for username: {username}")
            return False, "Invalid username or password.", None

        admin = Admin.from_row(row)
        if verify_password(plain_password, admin.password_hash, admin.salt):
            self._reset_failed_attempts(f"admin:{username}")
            log_event("INFO", f"Admin '{admin.username}' logged in successfully.")
            return True, f"Welcome back, {admin.full_name}!", admin
        else:
            self._record_failed_attempt(f"admin:{username}")
            log_event("WARNING", f"Incorrect password for admin user: {username}")
            return False, "Invalid username or password.", None

    def login_member(self, username: str, plain_password: str) -> Tuple[bool, str, Optional[Member]]:
        """
        Authenticate a library member.
        """
        if not username or not plain_password:
            return False, "Username and password are required.", None

        locked, remaining = self._check_lockout(f"member:{username}")
        if locked:
            return False, f"Too many failed login attempts. Please wait {remaining} seconds before trying again.", None

        row = self.db.fetch_one(
            "SELECT * FROM members WHERE username = ? COLLATE NOCASE",
            (username.strip(),)
        )

        if not row:
            self._record_failed_attempt(f"member:{username}")
            log_event("WARNING", f"Failed member login attempt for username: {username}")
            return False, "Invalid username or password.", None

        member = Member.from_row(row)
        if not verify_password(plain_password, member.password_hash, member.salt):
            self._record_failed_attempt(f"member:{username}")
            log_event("WARNING", f"Incorrect password for member: {username}")
            return False, "Invalid username or password.", None

        if not member.is_active:
            log_event("WARNING", f"Blocked member '{member.member_id}' attempted to log in.")
            return False, "Your account is currently BLOCKED. Please contact the librarian.", None

        self._reset_failed_attempts(f"member:{username}")
        log_event("INFO", f"Member '{member.member_id}' ({member.full_name}) logged in successfully.")
        return True, f"Welcome, {member.full_name}!", member

    def register_member(
        self,
        full_name: str,
        member_id: str,
        cnic: str,
        phone: str,
        email: str,
        address: str,
        username: str,
        password: str,
        confirm_password: str
    ) -> Tuple[bool, str, Optional[Member]]:
        """
        Register a new library member with comprehensive validation.
        """
        # 1. Validation checks
        valid_name, err_name = validate_name(full_name)
        if not valid_name:
            return False, err_name, None

        if not member_id or not member_id.strip():
            return False, "Member ID cannot be empty.", None
        member_id = member_id.strip().upper()

        valid_cnic, err_cnic = validate_cnic(cnic)
        if not valid_cnic:
            return False, err_cnic, None
        cnic = cnic.strip()

        valid_phone, err_phone = validate_phone(phone)
        if not valid_phone:
            return False, err_phone, None
        phone = phone.strip()

        valid_email, err_email = validate_email(email)
        if not valid_email:
            return False, err_email, None
        email = email.strip().lower()

        if not address or not address.strip():
            return False, "Address cannot be empty.", None
        address = address.strip()

        valid_user, err_user = validate_username(username)
        if not valid_user:
            return False, err_user, None
        username = username.strip().lower()

        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters long.", None

        if password != confirm_password:
            return False, "Passwords do not match.", None

        # 2. Uniqueness checks in database
        existing_user = self.db.fetch_one(
            "SELECT id FROM members WHERE username = ? COLLATE NOCASE",
            (username,)
        )
        if existing_user:
            return False, f"Username '{username}' is already taken. Please choose another.", None

        existing_mid = self.db.fetch_one(
            "SELECT id FROM members WHERE member_id = ? COLLATE NOCASE",
            (member_id,)
        )
        if existing_mid:
            return False, f"Member ID '{member_id}' is already registered.", None

        existing_cnic = self.db.fetch_one(
            "SELECT id FROM members WHERE cnic = ?",
            (cnic,)
        )
        if existing_cnic:
            return False, f"CNIC / Student ID '{cnic}' is already registered.", None

        # 3. Hash password and insert
        pwd_hash, salt = hash_password(password)

        try:
            member_db_id = self.db.execute_update(
                """
                INSERT INTO members (member_id, full_name, cnic, phone, email, address, username, password_hash, salt, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
                """,
                (member_id, full_name.strip(), cnic, phone, email, address, username, pwd_hash, salt)
            )
            log_event("INFO", f"New member registered: {member_id} ({full_name})")
            
            created_row = self.db.fetch_one("SELECT * FROM members WHERE id = ?", (member_db_id,))
            created_member = Member.from_row(created_row)
            return True, "Member registration successful! You can now log in.", created_member
        except Exception as e:
            log_event("ERROR", f"Failed to register member: {e}")
            return False, f"Registration failed due to a database error: {e}", None

    def change_password(
        self,
        user_type: str,  # 'admin' or 'member'
        user_id: int,
        old_password: str,
        new_password: str,
        confirm_new_password: str
    ) -> Tuple[bool, str]:
        """
        Change password for an authenticated user.
        """
        if not old_password or not new_password:
            return False, "Password fields cannot be empty."

        if len(new_password) < 4:
            return False, "New password must be at least 4 characters long."

        if new_password != confirm_new_password:
            return False, "New passwords do not match."

        table = "admins" if user_type == "admin" else "members"
        row = self.db.fetch_one(f"SELECT * FROM {table} WHERE id = ?", (user_id,))
        if not row:
            return False, "User account not found."

        stored_hash = row["password_hash"]
        salt = row["salt"]

        if not verify_password(old_password, stored_hash, salt):
            return False, "Current password is incorrect."

        new_hash, new_salt = hash_password(new_password)
        try:
            self.db.execute_update(
                f"UPDATE {table} SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user_id)
            )
            log_event("INFO", f"Password changed successfully for {user_type} ID: {user_id}")
            return True, "Password changed successfully."
        except Exception as e:
            log_event("ERROR", f"Error updating password: {e}")
            return False, "Failed to update password."
