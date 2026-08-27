"""
Validation utilities for inputs: names, emails, phones, CNIC, ISBNs, years, quantities, amounts.
"""

import datetime
from decimal import Decimal, InvalidOperation
import re


def validate_name(name: str) -> tuple[bool, str]:
    """Validate name contains alphabets, spaces, dots, or hyphens (min 2 chars)."""
    if not name or not name.strip():
        return False, "Name cannot be empty."
    name = name.strip()
    if len(name) < 2:
        return False, "Name must be at least 2 characters long."
    if not re.match(r"^[A-Za-z\s\.\'-]+$", name):
        return False, "Name can only contain alphabetic letters, spaces, dots, or hyphens."
    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username (3-30 chars, alphanumeric or underscores)."""
    if not username or not username.strip():
        return False, "Username cannot be empty."
    username = username.strip()
    if len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain alphanumeric characters and underscores."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email address format."""
    if not email or not email.strip():
        return False, "Email cannot be empty."
    email = email.strip()
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, email):
        return False, "Invalid email address format (e.g., user@example.com)."
    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validate phone number.
    Supports formats like 03001234567, 0300-1234567, +923001234567, +1234567890.
    """
    if not phone or not phone.strip():
        return False, "Phone number cannot be empty."
    phone_clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if not re.match(r"^(\+?\d{9,15})$", phone_clean):
        return False, "Invalid phone number (must contain 9-15 digits, optional leading +)."
    return True, ""


def validate_cnic(cnic: str) -> tuple[bool, str]:
    """
    Validate CNIC (e.g., 12345-1234567-1 or 13 digits) or Student ID format.
    """
    if not cnic or not cnic.strip():
        return False, "CNIC / Student ID cannot be empty."
    cnic_clean = cnic.strip()
    # Standard Pakistani CNIC format: 12345-1234567-1 or 13 digits
    if re.match(r"^\d{5}-\d{7}-\d{1}$", cnic_clean) or re.match(r"^\d{13}$", cnic_clean):
        return True, ""
    # Alternative Student ID format (e.g. STU-1001, CS2023-01)
    if re.match(r"^[A-Za-z0-9\-_]{4,20}$", cnic_clean):
        return True, ""
    return False, "Invalid format. Expected CNIC (XXXXX-XXXXXXX-X) or Student ID (4-20 alphanumeric chars)."


def validate_isbn(isbn: str) -> tuple[bool, str]:
    """
    Validate ISBN (ISBN-10 or ISBN-13 format, with or without hyphens).
    """
    if not isbn or not isbn.strip():
        return False, "ISBN cannot be empty."
    isbn_clean = re.sub(r"[\s\-]", "", isbn.strip()).upper()
    if len(isbn_clean) == 10:
        # ISBN-10: 9 digits + 1 digit or 'X'
        if not re.match(r"^\d{9}[\dX]$", isbn_clean):
            return False, "Invalid ISBN-10 format."
        return True, ""
    elif len(isbn_clean) == 13:
        # ISBN-13: 13 digits
        if not re.match(r"^\d{13}$", isbn_clean):
            return False, "Invalid ISBN-13 format (must be 13 digits)."
        return True, ""
    else:
        return False, "ISBN must be either 10 or 13 characters."


def validate_year(year_val: any) -> tuple[bool, str]:
    """Validate publication year (e.g., 1000 to current year + 1)."""
    try:
        y = int(year_val)
        current_year = datetime.datetime.now().year
        if y < 1000 or y > current_year + 1:
            return False, f"Publication year must be between 1000 and {current_year + 1}."
        return True, ""
    except (ValueError, TypeError):
        return False, "Year must be a valid 4-digit integer."


def validate_positive_int(val: any, field_name: str = "Value") -> tuple[bool, str, int]:
    """Validate that input is an integer > 0."""
    try:
        i = int(val)
        if i <= 0:
            return False, f"{field_name} must be greater than 0.", 0
        return True, "", i
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid positive integer.", 0


def validate_non_negative_decimal(val: any, field_name: str = "Amount") -> tuple[bool, str, Decimal]:
    """Validate decimal amount >= 0."""
    try:
        d = Decimal(str(val).strip())
        if d < 0:
            return False, f"{field_name} cannot be negative.", Decimal("0.00")
        return True, "", d.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return False, f"{field_name} must be a valid numerical amount.", Decimal("0.00")
