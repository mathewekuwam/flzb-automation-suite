import os
import sys
import time

# Force UTF-8 encoding for standard output on Windows to support block characters
if sys.stdout.encoding.lower() != 'utf-8':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# ANSI color codes for terminal output
BRIGHT_GREEN = "\033[92m"
DARK_GREEN = "\033[32m"
RESET = "\033[0m"

def type_print(text, delay=0.01):
    """Prints text character by character for a typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print() # Add a newline after the typed text

def print_banner():
    # Clear terminal screen (this also enables ANSI color codes in Windows cmd/powershell)
    os.system("cls" if os.name == "nt" else "clear")

    banner = f"""
{BRIGHT_GREEN}
███████╗██╗     ███████╗██████╗     ██████╗  ██████╗ ████████╗
██╔════╝██║     ╚══███╔╝██╔══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝
█████╗  ██║       ███╔╝ ██████╔╝    ██████╔╝██║   ██║   ██║   
██╔══╝  ██║      ███╔╝  ██╔══██╗    ██╔══██╗██║   ██║   ██║   
██║     ███████╗███████╗██████╔╝    ██████╔╝╚██████╔╝   ██║   
╚═╝     ╚══════╝╚══════╝╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   
{RESET}
"""

    type_print(banner, 0.0005)

    print(f"{DARK_GREEN}" + "═" * 70 + f"{RESET}")

    lines = [
        "[ FLZB BOT - MORELOGIN VERIFICATION AUTOMATION ]",
        "",
        "[FEATURES]",
        "✓ Selenium Browser Automation",
        "✓ MoreLogin API Integration",
        "✓ Automatic Verification",
        "✓ Match Detection",
        "✓ CSV Export",
        "✓ Debug Screenshot Capture",
        "✓ Attempts Logging",
        "",
        "[STATUS] READY",
    ]

    for line in lines:
        type_print(f"{BRIGHT_GREEN}{line}{RESET}", 0.01)

    print(f"{DARK_GREEN}" + "═" * 70 + f"{RESET}")

if __name__ == "__main__":
    print_banner()
