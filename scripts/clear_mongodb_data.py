#!/usr/bin/env python3
"""
Clear All Data from MongoDB Collections
Removes all documents from collections while preserving indexes and structure
Use this to reset the database for testing data generation
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
    print("Clear MongoDB Collections - Data Reset")
    print("="*60 + "\n")

    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    connection_string = os.getenv('MONGODB_CONNECTION_STRING')
    database_name = os.getenv('MONGODB_DATABASE', 'retail-demo')

    if not connection_string:
        print(f"{RED}✗ MONGODB_CONNECTION_STRING not found in .env{RESET}")
        sys.exit(1)

    print(f"{YELLOW}⚠ WARNING: This will delete ALL data from these collections:{RESET}")
    print(f"  Database: {BLUE}{database_name}{RESET}")
    print(f"\n  Collections:")
    print(f"    • stores")
    print(f"    • customers")
    print(f"    • categories")
    print(f"    • products")
    print(f"    • product_embeddings")
    print(f"    • inventory")
    print(f"    • orders")
    print(f"    • order_items")
    print(f"\n{YELLOW}  Indexes and collection structure will be preserved.{RESET}")
    print(f"\n{RED}  This action CANNOT be undone!{RESET}\n")

    # Confirmation
    response = input(f"{BLUE}Type 'DELETE ALL DATA' to confirm: {RESET}").strip()
    if response != 'DELETE ALL DATA':
        print(f"\n{YELLOW}Aborted. No data was deleted.{RESET}\n")
        sys.exit(0)

    print(f"\n{BLUE}ℹ Connecting to MongoDB...{RESET}")
    client = MongoClient(connection_string)
    db = client[database_name]

    print(f"{GREEN}✓ Connected to database: {database_name}{RESET}\n")

    # Collections to clear
    collections = [
        'stores',
        'customers',
        'categories',
        'products',
        'product_embeddings',
        'inventory',
        'orders',
        'order_items'
    ]

    print(f"{BLUE}Deleting all documents from collections...{RESET}\n")

    total_deleted = 0
    success_count = 0
    error_count = 0

    for collection_name in collections:
        try:
            # Get document count before deletion
            doc_count = db[collection_name].count_documents({})

            if doc_count == 0:
                print(f"{YELLOW}  ⚠ {collection_name}: Already empty{RESET}")
                success_count += 1
                continue

            print(f"{BLUE}  Processing: {collection_name}...{RESET}")
            print(f"    Documents before: {doc_count:,}")

            # Delete all documents
            result = db[collection_name].delete_many({})
            deleted = result.deleted_count
            total_deleted += deleted

            # Verify deletion
            remaining = db[collection_name].count_documents({})

            if remaining == 0:
                print(f"{GREEN}    ✓ Deleted: {deleted:,} documents{RESET}")
                success_count += 1
            else:
                print(f"{YELLOW}    ⚠ Deleted: {deleted:,}, Remaining: {remaining:,}{RESET}")
                success_count += 1

        except Exception as e:
            print(f"{RED}    ✗ Error: {e}{RESET}")
            error_count += 1

        print()

    print("="*60)
    print("Summary")
    print("="*60)
    print(f"{GREEN}✓ Collections cleared: {success_count}/{len(collections)}{RESET}")
    if error_count > 0:
        print(f"{RED}✗ Errors: {error_count}{RESET}")
    print(f"{GREEN}Total documents deleted: {total_deleted:,}{RESET}")
    print()

    # Check indexes are still present
    print(f"{BLUE}Verifying indexes are preserved...{RESET}\n")

    index_count = 0
    for collection_name in collections:
        indexes = list(db[collection_name].list_indexes())
        index_count += len(indexes)
        print(f"  {collection_name}: {len(indexes)} indexes")

    print(f"\n{GREEN}✓ Total indexes preserved: {index_count}{RESET}")

    if error_count == 0:
        print(f"\n{GREEN}Database cleared successfully!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Re-generate data: python scripts/generate_mongodb_data.py")
        print("  2. Verify data: python scripts/test_connection.py")
    else:
        print(f"\n{RED}Some collections failed to clear. Check errors above.{RESET}")
        sys.exit(1)

    print("\n" + "="*60 + "\n")
    client.close()

if __name__ == '__main__':
    main()
