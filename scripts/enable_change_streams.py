#!/usr/bin/env python3
"""
Enable Change Streams on MongoDB Collections
Required for Ditto MongoDB Connector to capture real-time changes
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import sys

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def main():
    print("\n" + "="*60)
    print("Enable Change Streams on MongoDB Collections")
    print("="*60 + "\n")

    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    connection_string = os.getenv('MONGODB_CONNECTION_STRING')
    database_name = os.getenv('MONGODB_DATABASE', 'retail-demo')

    if not connection_string:
        print(f"{RED}✗ MONGODB_CONNECTION_STRING not found in .env{RESET}")
        sys.exit(1)

    print(f"{BLUE}ℹ Connecting to MongoDB...{RESET}")
    client = MongoClient(connection_string)
    db = client[database_name]

    print(f"{GREEN}✓ Connected to database: {database_name}{RESET}\n")

    # Collections that need change streams enabled
    collections = [
        'stores',
        'customers',
        'categories',
        'products',
        'inventory',
        'orders',
        'order_items'
    ]

    print(f"{BLUE}Enabling change streams with pre/post images...{RESET}\n")

    success_count = 0
    error_count = 0

    for collection_name in collections:
        try:
            # Enable change streams with pre and post images
            result = db.command({
                'collMod': collection_name,
                'changeStreamPreAndPostImages': {'enabled': True}
            })

            if result.get('ok') == 1:
                print(f"{GREEN}✓ Enabled change streams on: {collection_name}{RESET}")
                success_count += 1
            else:
                print(f"{YELLOW}⚠ Unexpected response for {collection_name}: {result}{RESET}")
                error_count += 1

        except Exception as e:
            error_str = str(e)
            if 'AtlasError' in error_str and 'collMod' in error_str:
                print(f"{RED}✗ Permission denied for {collection_name}{RESET}")
                print(f"{YELLOW}  MongoDB user needs 'dbAdmin' or 'atlasAdmin' role{RESET}")
                error_count += 1
            else:
                print(f"{RED}✗ Failed to enable change streams on {collection_name}: {e}{RESET}")
                error_count += 1

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"{GREEN}✓ Success: {success_count} collections{RESET}")
    if error_count > 0:
        print(f"{RED}✗ Errors: {error_count} collections{RESET}")
    print()

    if error_count == 0:
        print(f"{GREEN}All change streams enabled successfully!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Verify with: python scripts/test_change_streams.py")
        print("  2. Configure connector in Ditto Portal: https://portal.ditto.live")
        print("  3. Run initial sync: python scripts/trigger_initial_sync.py")
    else:
        print(f"{RED}Some collections failed. Check errors above.{RESET}\n")

        # Check if this is a permissions issue
        if "Permission denied" in str(error_count):
            print(f"{YELLOW}Permission Error - Manual Setup Required{RESET}")
            print(f"\n{BLUE}Option 1: Grant Database Admin Role{RESET}")
            print("  1. Log in to MongoDB Atlas")
            print("  2. Go to Database Access")
            print("  3. Edit user 'ditto-demo'")
            print("  4. Add 'dbAdmin' role for 'retail-demo' database")
            print("  5. Re-run this script")

            print(f"\n{BLUE}Option 2: Enable Change Streams via Atlas UI{RESET}")
            print("  1. Log in to MongoDB Atlas")
            print("  2. Go to Clusters → Collections")
            print("  3. Select 'retail-demo' database")
            print("  4. For each collection, click options (⋮) → Collection Settings")
            print("  5. Enable 'Change Stream Pre- and Post-Images'")
            print("  6. Repeat for all 7 collections")

            print(f"\n{BLUE}Option 3: Use MongoDB Atlas CLI{RESET}")
            print("  atlas clusters changeStreams enable \\")
            print("    --clusterName <your-cluster> \\")
            print("    --database retail-demo \\")
            print("    --collection <collection-name>")

        sys.exit(1)

    print("\n" + "="*60 + "\n")
    client.close()

if __name__ == '__main__':
    main()
