#!/usr/bin/env python3
"""
generate_admin_hash.py
Run once to create your admin password hash.
Add the output to your .env as ADMIN_PASSWORD_HASH.

Usage:
    python generate_admin_hash.py
"""
import getpass
import bcrypt

def main():
    print("=== MK Portfolio · Admin Password Setup ===\n")
    while True:
        pw  = getpass.getpass("Enter new admin password: ")
        pw2 = getpass.getpass("Confirm password:         ")
        if pw != pw2:
            print("Passwords do not match. Try again.\n")
            continue
        if len(pw) < 10:
            print("Password must be at least 10 characters.\n")
            continue
        break

    hashed = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12))
    print("\n✅ Add this to your .env file:\n")
    print(f'ADMIN_PASSWORD_HASH="{hashed.decode()}"')
    print("\nKeep this hash secret. Never commit it to git.")

if __name__ == "__main__":
    main()