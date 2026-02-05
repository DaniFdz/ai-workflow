#!/usr/bin/env python3
"""
Check if pi coding agent is installed and available.

Usage:
    python3 check_pi.py

Exit codes:
    0 - Pi coding agent found
    1 - Pi coding agent not found
"""

import subprocess
import sys
import shutil


def check_pi_installation() -> bool:
    """
    Check if pi coding agent is installed and accessible.

    Returns:
        True if pi is installed, False otherwise
    """
    # Check if pi is in PATH
    pi_path = shutil.which("pi")

    if not pi_path:
        print("Pi coding agent not found in PATH.")
        print("")
        print("Installation instructions:")
        print("  1. Ensure Node.js 20+ is installed:")
        print("     node --version")
        print("")
        print("  2. Install pi coding agent globally:")
        print("     npm install -g @mariozechner/pi-coding-agent")
        print("")
        print("  3. Verify installation:")
        print("     pi --version")
        print("")
        print("For more information, visit:")
        print("  https://github.com/badlogic/pi-mono")
        return False

    # Try to get version
    try:
        result = subprocess.run(
            ["pi", "--version"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            print(f"Pi coding agent found: {version}")
            print(f"Location: {pi_path}")
            return True
        else:
            # pi exists but --version failed (might still work)
            print(f"Pi coding agent found at: {pi_path}")
            print("Warning: Could not determine version")
            return True

    except subprocess.TimeoutExpired:
        print(f"Pi coding agent found at: {pi_path}")
        print("Warning: Version check timed out")
        return True
    except Exception as e:
        print(f"Error checking pi version: {e}")
        return False


def main():
    """Main entry point."""
    if check_pi_installation():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
