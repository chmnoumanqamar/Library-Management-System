"""
CLI formatting, table rendering, input prompts, and display helpers.
Provides elegant UI elements with Unicode box-drawing and optional ANSI color support.
"""

import datetime
from decimal import Decimal
import os
import sys
from config import CURRENCY_SYMBOL, ENABLE_ANSI_COLORS, TERMINAL_WIDTH

# ANSI Color Codes
if ENABLE_ANSI_COLORS and sys.stdout.isatty():
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BG_BLUE = "\033[44m"
else:
    RESET = ""
    BOLD = ""
    DIM = ""
    CYAN = ""
    BLUE = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    MAGENTA = ""
    BG_BLUE = ""


def clear_screen() -> None:
    """Clear terminal screen cross-platform."""
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def pause(message: str = "Press Enter to continue...") -> None:
    """Pause execution until the user presses Enter."""
    try:
        input(f"\n{DIM}{message}{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


def print_banner(title: str, width: int = 60) -> None:
    """Print an eye-catching header banner."""
    print()
    print(f"{CYAN}{'=' * width}{RESET}")
    print(f"{BOLD}{CYAN}{title.center(width)}{RESET}")
    print(f"{CYAN}{'=' * width}{RESET}")
    print()


def print_section(title: str, width: int = 60) -> None:
    """Print a section sub-header."""
    print()
    print(f"{BLUE}{'-' * width}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BLUE}{'-' * width}{RESET}")


def print_success(message: str) -> None:
    """Print a green success notification."""
    print(f"\n{GREEN}✔ [SUCCESS]{RESET} {message}")


def print_error(message: str) -> None:
    """Print a red error notification."""
    print(f"\n{RED}✖ [ERROR]{RESET} {message}")


def print_warning(message: str) -> None:
    """Print a yellow warning notification."""
    print(f"\n{YELLOW}⚠ [WARNING]{RESET} {message}")


def print_info(message: str) -> None:
    """Print a cyan informational note."""
    print(f"\n{CYAN}ℹ [INFO]{RESET} {message}")


def format_date(dt_val: any, target_format: str = "%d-%b-%Y") -> str:
    """
    Format date string or datetime object to readable string (e.g. 27-Aug-2026).
    """
    if not dt_val:
        return "N/A"
    if isinstance(dt_val, (datetime.date, datetime.datetime)):
        return dt_val.strftime(target_format)
    
    str_val = str(dt_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            parsed = datetime.datetime.strptime(str_val, fmt)
            return parsed.strftime(target_format)
        except ValueError:
            continue
    return str_val


def format_currency(amount: any) -> str:
    """Format decimal/float amount into localized currency string."""
    try:
        val = Decimal(str(amount))
        return f"{CURRENCY_SYMBOL} {val:,.2f}"
    except Exception:
        return f"{CURRENCY_SYMBOL} {amount}"


def prompt_string(prompt: str, required: bool = True, default: str = None) -> str:
    """Safely prompt user for string input."""
    while True:
        try:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if required and not user_input:
                print(f"{RED}This field is required. Please try again.{RESET}")
                continue
            return user_input
        except (KeyboardInterrupt, EOFError):
            print()
            raise


def prompt_choice(prompt: str = "Enter your choice: ") -> str:
    """Prompt user for menu selection choice."""
    try:
        return input(f"{BOLD}{prompt}{RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        raise


def prompt_confirmation(message: str, default: bool = False) -> bool:
    """
    Prompt user for a confirmation dialog (Y/N).
    """
    hint = " [Y/n]" if default else " [y/N]"
    while True:
        try:
            ans = input(f"{YELLOW}{message}{hint}: {RESET}").strip().lower()
            if not ans:
                return default
            if ans in ("y", "yes"):
                return True
            if ans in ("n", "no"):
                return False
            print(f"{RED}Please enter 'y' for Yes or 'n' for No.{RESET}")
        except (KeyboardInterrupt, EOFError):
            print()
            raise


def print_table(headers: list[str], rows: list[list[any]], empty_message: str = "No records found.") -> None:
    """
    Print an elegant ASCII/Unicode formatted table with auto-adjusting column widths.
    """
    if not rows:
        print(f"\n{YELLOW}{empty_message}{RESET}\n")
        return

    # Calculate column widths
    num_cols = len(headers)
    col_widths = [len(str(h)) for h in headers]
    
    formatted_rows = []
    for row in rows:
        formatted_row = [str(item) if item is not None else "" for item in row]
        # Pad row if less columns
        if len(formatted_row) < num_cols:
            formatted_row += [""] * (num_cols - len(formatted_row))
        formatted_rows.append(formatted_row[:num_cols])
        
        for i, val in enumerate(formatted_row[:num_cols]):
            col_widths[i] = max(col_widths[i], len(val))

    # Cap excessive column widths to maintain readability on standard screens
    max_col_width = 32
    col_widths = [min(w, max_col_width) for w in col_widths]

    # Build border lines
    top_border = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    header_sep = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    bottom_border = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"

    print()
    print(f"{CYAN}{top_border}{RESET}")
    
    # Header row
    header_line = "│" + "│".join(
        f" {BOLD}{headers[i]:<{col_widths[i]}}{RESET} " for i in range(num_cols)
    ) + "│"
    print(f"{CYAN}{header_line}{RESET}")
    print(f"{CYAN}{header_sep}{RESET}")

    # Data rows
    for r in formatted_rows:
        row_str = "│"
        for i in range(num_cols):
            cell = r[i]
            if len(cell) > col_widths[i]:
                cell = cell[:col_widths[i] - 2] + ".."
            row_str += f" {cell:<{col_widths[i]}} │"
        print(row_str)

    print(f"{CYAN}{bottom_border}{RESET}")
    print(f"{DIM}Total records: {len(rows)}{RESET}\n")


def print_key_value_card(title: str, data: dict[str, any], width: int = 56) -> None:
    """Print a card view with key-value pairs."""
    print()
    print(f"{CYAN}{'=' * width}{RESET}")
    print(f"{BOLD}{CYAN}{title.center(width)}{RESET}")
    print(f"{CYAN}{'=' * width}{RESET}")
    
    max_key_len = max([len(str(k)) for k in data.keys()]) if data else 15
    for k, v in data.items():
        print(f"  {BOLD}{k:<{max_key_len}}{RESET} : {v}")
    print(f"{CYAN}{'=' * width}{RESET}\n")
