"""
Library Management System - Configuration Module
Centralized settings, business rules constants, and file paths.
"""

from decimal import Decimal
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database & Log file paths
DB_NAME = os.path.join(BASE_DIR, "library_management.db")
LOG_FILE = os.path.join(BASE_DIR, "library_management.log")
EXPORTS_DIR = os.path.join(BASE_DIR, "data")

# Ensure exports directory exists
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Business Rules Constants
MAX_BOOKS_PER_MEMBER = 5
DEFAULT_BORROWING_PERIOD_DAYS = 14
MAX_RENEWALS = 2
FINE_PER_OVERDUE_DAY = Decimal("20.00")
CURRENCY_SYMBOL = "Rs."

# Security & Authentication Settings
PASSWORD_HASH_ITERATIONS = 100_000
PASSWORD_SALT_BYTES = 16
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 30

# UI & Display Settings
ENABLE_ANSI_COLORS = True
PAGE_SIZE = 10
TERMINAL_WIDTH = 78
