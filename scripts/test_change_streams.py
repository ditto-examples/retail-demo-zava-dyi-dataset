#!/usr/bin/env python3
"""
Test MongoDB Change Streams
Verifies that change streams are enabled and working on all collections
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
    print("Test MongoDB Change Streams")
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

    # Collections to test
    collections = [
        'stores',
        'customers',
        'categories',
        'products',
        'inventory',
        'orders',
        'order_items'
    ]

    print(f"{BLUE}Testing change streams on collections...{RESET}\n")

    success_count = 0
    error_count = 0

    for collection_name in collections:
        try:
            # Get collection info
            coll_info = db.command({'listCollections': 1, 'filter': {'name': collection_name}})

            if not coll_info.get('cursor', {}).get('firstBatch'):
                print(f"{RED}✗ Collection not found: {collection_name}{RESET}")
                error_count += 1
                continue

            collection_data = coll_info['cursor']['firstBatch'][0]
            options = collection_data.get('options', {})
            change_stream_enabled = options.get('changeStreamPreAndPostImages', {}).get('enabled', False)

            if change_stream_enabled:
                print(f"{GREEN}✓ Change streams enabled on: {collection_name}{RESET}")
                success_count += 1
            else:
                print(f"{RED}✗ Change streams NOT enabled on: {collection_name}{RESET}")
                print(f"  Run: python scripts/enable_change_streams.py")
                error_count += 1

        except Exception as e:
            print(f"{RED}✗ Error testing {collection_name}: {e}{RESET}")
            error_count += 1

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"{GREEN}✓ Success: {success_count} collections{RESET}")
    if error_count > 0:
        print(f"{RED}✗ Errors: {error_count} collections{RESET}")
    print()

    if error_count == 0:
        print(f"{GREEN}All change streams are enabled and ready!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Deploy Ditto connector: docker-compose up -d")
        print("  2. Run initial sync: python scripts/trigger_initial_sync.py")
    else:
        print(f"{RED}Some collections don't have change streams enabled.{RESET}")
        print(f"{BLUE}Run: python scripts/enable_change_streams.py{RESET}")
        sys.exit(1)

    print("\n" + "="*60 + "\n")
    client.close()

if __name__ == '__main__':
    main()
