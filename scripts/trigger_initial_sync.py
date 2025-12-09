#!/usr/bin/env python3
"""
Trigger Initial Sync for Ditto Connector
Updates all documents to trigger MongoDB change streams for initial sync
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz
import sys

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def main():
    print("\n" + "="*60)
    print("Trigger Initial Sync for Ditto Connector")
    print("="*60 + "\n")

    print(f"{YELLOW}⚠ WARNING: This will update all documents to trigger sync.{RESET}")
    print(f"{YELLOW}  This is required for existing data to sync to Ditto.{RESET}\n")

    response = input(f"{BLUE}Continue? (yes/no): {RESET}").strip().lower()
    if response not in ['yes', 'y']:
        print(f"\n{RED}Aborted.{RESET}\n")
        sys.exit(0)

    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    connection_string = os.getenv('MONGODB_CONNECTION_STRING')
    database_name = os.getenv('MONGODB_DATABASE', 'retail-demo')

    if not connection_string:
        print(f"\n{RED}✗ MONGODB_CONNECTION_STRING not found in .env{RESET}\n")
        sys.exit(1)

    print(f"\n{BLUE}ℹ Connecting to MongoDB...{RESET}")
    client = MongoClient(connection_string)
    db = client[database_name]

    print(f"{GREEN}✓ Connected to database: {database_name}{RESET}\n")

    # Collections to sync (excluding product_embeddings - not synced to Ditto)
    collections = [
        'stores',
        'customers',
        'categories',
        'products',
        'inventory',
        'orders',
        'order_items'
    ]

    print(f"{BLUE}Triggering sync by touching all documents...{RESET}\n")

    total_updated = 0
    success_count = 0
    error_count = 0

    for collection_name in collections:
        try:
            print(f"{BLUE}Processing: {collection_name}...{RESET}")

            # Count documents
            doc_count = db[collection_name].count_documents({})
            print(f"  Documents: {doc_count:,}")

            if doc_count == 0:
                print(f"{YELLOW}  ⚠ Empty collection, skipping{RESET}")
                continue

            # Update all documents with a sync timestamp
            now = datetime.now(pytz.UTC).isoformat()
            result = db[collection_name].update_many(
                {},  # Match all documents
                {
                    '$set': {
                        '_ditto_sync_triggered': now
                    }
                }
            )

            updated = result.modified_count
            total_updated += updated

            if updated == doc_count:
                print(f"{GREEN}  ✓ Updated: {updated:,} documents{RESET}\n")
                success_count += 1
            else:
                print(f"{YELLOW}  ⚠ Updated: {updated:,} / {doc_count:,} documents{RESET}\n")
                success_count += 1

        except Exception as e:
            print(f"{RED}  ✗ Error: {e}{RESET}\n")
            error_count += 1

    print("="*60)
    print("Summary")
    print("="*60)
    print(f"{GREEN}✓ Collections processed: {success_count}{RESET}")
    if error_count > 0:
        print(f"{RED}✗ Errors: {error_count}{RESET}")
    print(f"{GREEN}Total documents updated: {total_updated:,}{RESET}")
    print()

    if error_count == 0:
        print(f"{GREEN}Initial sync triggered successfully!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Monitor sync progress in Ditto Portal: https://portal.ditto.live")
        print("  2. Check connector logs in Portal (Settings → MongoDB Connector)")
        print("  3. Verify document counts match between MongoDB and Ditto")
    else:
        print(f"{RED}Some collections failed. Check errors above.{RESET}")
        sys.exit(1)

    print("\n" + "="*60 + "\n")
    client.close()

if __name__ == '__main__':
    main()
