"""
Main Entry Menu Gateway.
Provides initial landing portal, admin/member authentication routing, and registration.
"""

from cli.admin_menu import AdminMenu
from cli.member_menu import MemberMenu
from services.auth_service import AuthService
from utils.helpers import (
    BOLD,
    CYAN,
    RESET,
    clear_screen,
    pause,
    print_banner,
    print_error,
    print_info,
    print_key_value_card,
    print_success,
    prompt_choice,
    prompt_string,
)
from utils.security import get_secure_password


class MainMenu:
    """
    Main Navigation Controller.
    """
    def __init__(self):
        self.auth_service = AuthService()

    def run(self) -> None:
        """Main interaction loop."""
        while True:
            clear_screen()
            print_banner("LIBRARY MANAGEMENT SYSTEM", width=60)
            print(f" {BOLD}1. Admin Login{RESET}")
            print(f" {BOLD}2. Member Login{RESET}")
            print(f" {BOLD}3. Member Registration{RESET}")
            print(f" {BOLD}4. Exit Application{RESET}")
            print()
            print(f"{CYAN}{'=' * 60}{RESET}")

            choice = prompt_choice("Enter your choice (1-4): ")

            if choice == "1":
                self.admin_login_flow()
            elif choice == "2":
                self.member_login_flow()
            elif choice == "3":
                self.member_registration_flow()
            elif choice == "4":
                self.exit_app()
                break
            else:
                print_error("Invalid option. Please enter a choice between 1 and 4.")
                pause()

    def admin_login_flow(self) -> None:
        """Admin authentication workflow."""
        clear_screen()
        print_banner("ADMINISTRATOR LOGIN")
        username = prompt_string("Enter Admin Username")
        password = get_secure_password("Enter Admin Password: ")

        success, msg, admin = self.auth_service.login_admin(username, password)
        if success and admin:
            print_success(msg)
            pause("Press Enter to launch Admin Dashboard...")
            admin_menu = AdminMenu(admin)
            admin_menu.run()
        else:
            print_error(msg)
            pause()

    def member_login_flow(self) -> None:
        """Member authentication workflow."""
        clear_screen()
        print_banner("MEMBER PORTAL LOGIN")
        username = prompt_string("Enter Member Username")
        password = get_secure_password("Enter Member Password: ")

        success, msg, member = self.auth_service.login_member(username, password)
        if success and member:
            print_success(msg)
            pause("Press Enter to enter Member Portal...")
            member_menu = MemberMenu(member)
            member_menu.run()
        else:
            print_error(msg)
            pause()

    def member_registration_flow(self) -> None:
        """New member registration workflow."""
        clear_screen()
        print_banner("NEW MEMBER REGISTRATION")
        print_info("Please provide the required membership details below:\n")

        full_name = prompt_string("Full Name (e.g. Ali Khan)")
        member_id = prompt_string("Member ID / Student ID (e.g. MEM-1005)")
        cnic = prompt_string("CNIC (XXXXX-XXXXXXX-X) or Student Roll No")
        phone = prompt_string("Phone Number (e.g. 0300-1234567)")
        email = prompt_string("Email Address (e.g. user@example.com)")
        address = prompt_string("Home / Campus Address")
        username = prompt_string("Choose Username (alphanumeric)")
        password = get_secure_password("Choose Password (min 4 chars): ")
        confirm_pwd = get_secure_password("Confirm Password: ")

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

        if success and member:
            print_success(msg)
            print_key_value_card("REGISTERED ACCOUNT SUMMARY", member.to_dict())
        else:
            print_error(msg)
        pause()

    def exit_app(self) -> None:
        """Graceful shutdown banner."""
        clear_screen()
        print()
        print(f"{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}{'THANK YOU FOR USING LIBRARY MANAGEMENT SYSTEM'.center(60)}{RESET}")
        print(f"{CYAN}{'=' * 60}{RESET}")
        print("\nAll database transactions committed and resources safely closed.\nGoodbye!\n")
