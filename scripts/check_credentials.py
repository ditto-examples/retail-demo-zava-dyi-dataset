#!/usr/bin/env python3
"""
Check and display MongoDB connection string details (for debugging)
This helps verify the connection string is properly formatted
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def main():
    print("\n" + "="*60)
    print("MongoDB Connection String Validator")
    print("="*60 + "\n")

    # Load .env file
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    conn_string = os.getenv('MONGODB_CONNECTION_STRING')

    if not conn_string:
        print(f"{RED}✗ MONGODB_CONNECTION_STRING not found in .env{RESET}")
        return

    print(f"{GREEN}✓ Found connection string in .env{RESET}\n")

    # Parse the connection string
    # Format: mongodb+srv://username:password@cluster.mongodb.net/

    # Use regex to extract parts
    pattern = r'mongodb(?:\+srv)?://([^:]+):([^@]+)@([^/]+)/?(.*)$'
    match = re.match(pattern, conn_string)

    if not match:
        print(f"{RED}✗ Connection string format is invalid{RESET}")
        print(f"\nExpected format:")
        print(f"  mongodb+srv://username:password@cluster.mongodb.net/")
        print(f"\nYour connection string:")
        print(f"  {conn_string}")
        return

    username = match.group(1)
    password = match.group(2)
    host = match.group(3)
    database = match.group(4) or "(default)"

    print("-"*60)
    print("Connection String Details:")
    print("-"*60)
    print(f"Username:  {BLUE}{username}{RESET}")
    print(f"Password:  {BLUE}{'*' * min(len(password), 20)}{RESET} ({len(password)} characters)")
    print(f"Host:      {BLUE}{host}{RESET}")
    print(f"Database:  {BLUE}{database}{RESET}")
    print()

    # Check for common issues
    print("-"*60)
    print("Validation Checks:")
    print("-"*60)

    issues = []

    # Check if password has unencoded special characters
    if any(char in password for char in ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '+', '/', ':']):
        issues.append(f"{YELLOW}⚠ Password contains special characters that may not be encoded{RESET}")
        issues.append(f"  Characters found: {', '.join([c for c in ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '+', '/', ':'] if c in password])}")
        issues.append(f"  Run: python scripts/encode_password.py")

    # Check if username has special characters (should be encoded too)
    if any(char in username for char in ['@', ':', '/']):
        issues.append(f"{YELLOW}⚠ Username contains special characters that should be encoded{RESET}")

    # Check host format
    if not host.endswith('.mongodb.net'):
        issues.append(f"{YELLOW}⚠ Host doesn't end with .mongodb.net (unusual for Atlas){RESET}")

    # Check if using placeholder values
    if 'username' in username.lower() or username == '<username>':
        issues.append(f"{RED}✗ Username appears to be a placeholder - replace with actual username{RESET}")

    if 'password' in password.lower() or password == '<password>':
        issues.append(f"{RED}✗ Password appears to be a placeholder - replace with actual password{RESET}")

    if 'cluster.mongodb.net' in host or 'cluster0.mongodb.net' in host:
        issues.append(f"{YELLOW}⚠ Cluster name may be generic - verify this is your actual cluster{RESET}")

    if issues:
        print(f"\n{len(issues)} issue(s) detected:\n")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"{GREEN}✓ No obvious issues detected{RESET}")

    print("\n" + "-"*60)
    print("Next Steps:")
    print("-"*60)
    print("1. Verify username exists in MongoDB Atlas → Database Access")
    print("2. Verify cluster name is correct → Clusters page")
    print("3. Test connection: python scripts/test_connection.py")
    print("4. If still failing, try resetting password in Atlas")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
