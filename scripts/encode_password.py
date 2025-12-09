#!/usr/bin/env python3
"""
Helper script to URL-encode MongoDB password for connection string
MongoDB Atlas connection strings require passwords with special characters to be URL-encoded
"""

import urllib.parse
import sys

def main():
    print("\n" + "="*60)
    print("MongoDB Password URL Encoder")
    print("="*60 + "\n")

    print("This script helps you encode passwords with special characters")
    print("for MongoDB Atlas connection strings.\n")

    # Get password from user
    if len(sys.argv) > 1:
        # Password provided as command line argument
        password = sys.argv[1]
    else:
        # Prompt for password
        print("Enter your MongoDB Atlas password:")
        password = input("> ")

    if not password:
        print("\nError: No password provided")
        sys.exit(1)

    # Encode the password
    encoded_password = urllib.parse.quote_plus(password)

    # Display results
    print("\n" + "-"*60)
    print("Results:")
    print("-"*60)
    print(f"Original password:  {password}")
    print(f"Encoded password:   {encoded_password}")

    if password == encoded_password:
        print("\n✓ No special characters detected - password does not need encoding")
    else:
        print("\n✓ Password has been encoded")
        print("\nUpdate your .env file:")
        print(f"  mongodb+srv://username:{encoded_password}@cluster.mongodb.net/")

    print("\nCommon character encodings:")
    print("  ! → %21")
    print("  @ → %40")
    print("  # → %23")
    print("  $ → %24")
    print("  % → %25")
    print("  ^ → %5E")
    print("  & → %26")
    print("  * → %2A")
    print("  ( → %28")
    print("  ) → %29")
    print("  = → %3D")
    print("  + → %2B")
    print("  / → %2F")
    print("  : → %3A")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
