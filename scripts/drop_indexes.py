#!/usr/bin/env python3
"""
Drop All Indexes from MongoDB Collections
Removes all indexes except the default _id index
Use this when data model changes and indexes need to be recreated
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
    print("Drop MongoDB Indexes - Schema Change Utility")
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

    # Collections to process
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

    # First, show what will be dropped
    print(f"{BLUE}Current indexes in database:{RESET}\n")

    total_indexes = 0
    total_droppable = 0

    for collection_name in collections:
        indexes = list(db[collection_name].list_indexes())
        droppable = [idx for idx in indexes if idx['name'] != '_id_']

        total_indexes += len(indexes)
        total_droppable += len(droppable)

        if droppable:
            print(f"{BLUE}{collection_name}:{RESET} {len(indexes)} indexes ({len(droppable)} will be dropped)")
            for idx in droppable:
                keys = ', '.join([f"{k}: {v}" for k, v in idx.get('key', {}).items()])
                print(f"  • {idx['name']}: {{ {keys} }}")
        else:
            print(f"{YELLOW}{collection_name}:{RESET} {len(indexes)} indexes (only _id_ index)")
        print()

    print("="*60)
    print(f"Summary:")
    print(f"  Total indexes: {total_indexes}")
    print(f"  Default _id indexes: {len(collections)} (will be preserved)")
    print(f"  Custom indexes: {total_droppable} (will be dropped)")
    print("="*60 + "\n")

    if total_droppable == 0:
        print(f"{YELLOW}No custom indexes found. Nothing to drop.{RESET}\n")
        client.close()
        sys.exit(0)

    print(f"{YELLOW}⚠ WARNING: This will drop {total_droppable} custom indexes!{RESET}")
    print(f"\n{YELLOW}  The default _id index on each collection will be preserved.{RESET}")
    print(f"{YELLOW}  Change stream settings will be preserved.{RESET}")
    print(f"{YELLOW}  Collection data will NOT be affected.{RESET}\n")
    print(f"{BLUE}  To recreate indexes after dropping:{RESET}")
    print(f"    python scripts/create_indexes.py\n")
    print(f"{RED}  This action CANNOT be undone!{RESET}\n")

    # Confirmation
    response = input(f"{BLUE}Type 'DROP INDEXES' to confirm: {RESET}").strip()
    if response != 'DROP INDEXES':
        print(f"\n{YELLOW}Aborted. No indexes were dropped.{RESET}\n")
        sys.exit(0)

    print(f"\n{BLUE}Dropping indexes from collections...{RESET}\n")

    success_count = 0
    error_count = 0
    total_dropped = 0

    for collection_name in collections:
        try:
            # Get all indexes
            indexes = list(db[collection_name].list_indexes())
            droppable = [idx for idx in indexes if idx['name'] != '_id_']

            if not droppable:
                print(f"{YELLOW}  ⚠ {collection_name}: No custom indexes to drop{RESET}")
                success_count += 1
                continue

            print(f"{BLUE}  Processing: {collection_name}...{RESET}")
            print(f"    Indexes before: {len(indexes)}")

            # Drop each index (except _id_)
            dropped_in_collection = 0
            for idx in droppable:
                try:
                    db[collection_name].drop_index(idx['name'])
                    dropped_in_collection += 1
                    total_dropped += 1
                except Exception as e:
                    print(f"{RED}      ✗ Failed to drop {idx['name']}: {e}{RESET}")

            # Verify
            remaining_indexes = list(db[collection_name].list_indexes())
            remaining_custom = [idx for idx in remaining_indexes if idx['name'] != '_id_']

            if len(remaining_custom) == 0:
                print(f"{GREEN}    ✓ Dropped: {dropped_in_collection} indexes{RESET}")
                print(f"    Remaining: {len(remaining_indexes)} (only _id_)")
                success_count += 1
            else:
                print(f"{YELLOW}    ⚠ Dropped: {dropped_in_collection}, Still remaining: {len(remaining_custom)} custom indexes{RESET}")
                success_count += 1

        except Exception as e:
            print(f"{RED}    ✗ Error: {e}{RESET}")
            error_count += 1

        print()

    print("="*60)
    print("Summary")
    print("="*60)
    print(f"{GREEN}✓ Collections processed: {success_count}/{len(collections)}{RESET}")
    if error_count > 0:
        print(f"{RED}✗ Errors: {error_count}{RESET}")
    print(f"{GREEN}Total indexes dropped: {total_dropped}{RESET}")
    print()

    # Verify final state
    print(f"{BLUE}Verifying final state...{RESET}\n")

    final_total = 0
    final_custom = 0

    for collection_name in collections:
        indexes = list(db[collection_name].list_indexes())
        custom = [idx for idx in indexes if idx['name'] != '_id_']
        final_total += len(indexes)
        final_custom += len(custom)

        if custom:
            print(f"  {collection_name}: {len(indexes)} indexes ({len(custom)} custom)")
        else:
            print(f"  {collection_name}: {len(indexes)} index (_id_ only)")

    print(f"\n{GREEN}✓ Total indexes remaining: {final_total} ({final_custom} custom, {len(collections)} default){RESET}")

    if error_count == 0 and final_custom == 0:
        print(f"\n{GREEN}All custom indexes dropped successfully!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Update data model/schema if needed")
        print("  2. Update scripts/create_indexes.py with new indexes")
        print("  3. Recreate indexes: python scripts/create_indexes.py")
        print("  4. Verify: python scripts/test_connection.py")
    elif final_custom > 0:
        print(f"\n{YELLOW}Warning: {final_custom} custom indexes still remain.{RESET}")
        print(f"Run this script again or manually drop them.")
    else:
        print(f"\n{RED}Some collections failed. Check errors above.{RESET}")
        sys.exit(1)

    print("\n" + "="*60 + "\n")
    client.close()

if __name__ == '__main__':
    main()
