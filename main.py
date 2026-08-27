"""
Library Management System - Main Entry Point.
Modular, Object-Oriented, CLI-Based Library Information System with SQLite3.
"""

import os
import signal
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.main_menu import MainMenu
from database import DatabaseManager
from seed_data import seed_database
from utils.helpers import BOLD, CYAN, RESET, clear_screen
from utils.logger import log_event


def handle_shutdown_signal(signum=None, frame=None) -> None:
    """Handle termination signals and Ctrl+C gracefully."""
    print(f"\n\n{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}{'Application closed safely.'.center(60)}{RESET}")
    print(f"{BOLD}{CYAN}{'Goodbye!'.center(60)}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")
    
    # Safely close DB
    try:
        db = DatabaseManager()
        db.close()
    except Exception:
        pass
    
    log_event("INFO", "Application terminated gracefully.")
    sys.exit(0)


def main() -> None:
    """Application bootstrap."""
    # Register signal handlers for clean exit
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        log_event("INFO", "=== Initializing Library Management System ===")
        
        # 1. Initialize SQLite Database Schema
        db = DatabaseManager()
        
        # 2. Seed initial demo data (Admin, Catalog, Members)
        seed_database()

        # 3. Launch Main CLI Application
        app = MainMenu()
        app.run()

    except KeyboardInterrupt:
        handle_shutdown_signal()
    except Exception as e:
        log_event("CRITICAL", f"Unhandled application exception: {e}")
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        try:
            db = DatabaseManager()
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
