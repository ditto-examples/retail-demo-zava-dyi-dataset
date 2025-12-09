#!/usr/bin/env python3
"""
MongoDB Index Creation Script
Creates all necessary indexes for optimal query performance
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
import sys

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def main():
    print("\n" + "="*60)
    print("Creating Indexes for MongoDB Collections")
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

    try:
        # ===================================================================
        # 1. STORES Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'stores' collection...{RESET}")
        db.stores.create_index([("store_id", ASCENDING)], unique=True, name="idx_store_id")
        db.stores.create_index([("deleted", ASCENDING)], name="idx_deleted")
        db.stores.create_index([("is_online", ASCENDING)], name="idx_is_online")
        print(f"{GREEN}✓ stores indexes created{RESET}\n")

        # ===================================================================
        # 2. CUSTOMERS Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'customers' collection...{RESET}")
        db.customers.create_index([("customer_id", ASCENDING)], unique=True, name="idx_customer_id")
        db.customers.create_index([("email", ASCENDING)], name="idx_email")
        db.customers.create_index([("primary_store_id", ASCENDING)], name="idx_primary_store_id")
        db.customers.create_index([("deleted", ASCENDING)], name="idx_deleted")
        db.customers.create_index([("last_name", ASCENDING), ("first_name", ASCENDING)], name="idx_name")
        print(f"{GREEN}✓ customers indexes created{RESET}\n")

        # ===================================================================
        # 3. CATEGORIES Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'categories' collection...{RESET}")
        db.categories.create_index([("category_id", ASCENDING)], unique=True, name="idx_category_id")
        db.categories.create_index([("deleted", ASCENDING)], name="idx_deleted")
        print(f"{GREEN}✓ categories indexes created{RESET}\n")

        # ===================================================================
        # 4. PRODUCTS Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'products' collection...{RESET}")
        db.products.create_index([("product_id", ASCENDING)], unique=True, name="idx_product_id")
        db.products.create_index([("sku", ASCENDING)], unique=True, name="idx_sku")
        db.products.create_index([("category_id", ASCENDING)], name="idx_category_id")
        db.products.create_index([("deleted", ASCENDING)], name="idx_deleted")

        # Text search index for product name and description
        db.products.create_index(
            [("product_name", TEXT), ("product_description", TEXT)],
            name="idx_text_search",
            weights={"product_name": 10, "product_description": 5}
        )
        print(f"{GREEN}✓ products indexes created{RESET}\n")

        # ===================================================================
        # 5. PRODUCT_EMBEDDINGS Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'product_embeddings' collection...{RESET}")
        db.product_embeddings.create_index([("product_id", ASCENDING)], unique=True, name="idx_product_id")
        print(f"{YELLOW}  ⚠ Vector search indexes require Atlas Search (create via UI){RESET}")
        print(f"{GREEN}✓ product_embeddings indexes created{RESET}\n")

        # ===================================================================
        # 6. INVENTORY Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'inventory' collection...{RESET}")
        db.inventory.create_index([("store_id", ASCENDING), ("product_id", ASCENDING)], unique=True, name="idx_store_product")
        db.inventory.create_index([("store_id", ASCENDING)], name="idx_store_id")
        db.inventory.create_index([("product_id", ASCENDING)], name="idx_product_id")
        db.inventory.create_index([("deleted", ASCENDING)], name="idx_deleted")

        # Low stock alerts
        db.inventory.create_index(
            [("store_id", ASCENDING), ("stock_level", ASCENDING), ("reorder_threshold", ASCENDING)],
            name="idx_low_stock"
        )

        # Location-based queries
        db.inventory.create_index([("location.aisle", ASCENDING)], name="idx_location_aisle")
        db.inventory.create_index([("location.shelf", ASCENDING)], name="idx_location_shelf")
        print(f"{GREEN}✓ inventory indexes created{RESET}\n")

        # ===================================================================
        # 7. ORDERS Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'orders' collection...{RESET}")
        db.orders.create_index([("order_id", ASCENDING)], unique=True, name="idx_order_id")
        db.orders.create_index([("customer_id", ASCENDING)], name="idx_customer_id")
        db.orders.create_index([("store_id", ASCENDING)], name="idx_store_id")
        db.orders.create_index([("order_date", DESCENDING)], name="idx_order_date_desc")
        db.orders.create_index([("deleted", ASCENDING)], name="idx_deleted")
        db.orders.create_index([("status", ASCENDING)], name="idx_status")

        # Compound indexes for common queries
        db.orders.create_index([("customer_id", ASCENDING), ("order_date", DESCENDING)], name="idx_customer_orders")
        db.orders.create_index([("store_id", ASCENDING), ("order_date", DESCENDING)], name="idx_store_orders")
        db.orders.create_index([("store_id", ASCENDING), ("status", ASCENDING)], name="idx_store_status")
        print(f"{GREEN}✓ orders indexes created{RESET}\n")

        # ===================================================================
        # 8. ORDER_ITEMS Collection
        # ===================================================================
        print(f"{BLUE}Creating indexes for 'order_items' collection...{RESET}")
        db.order_items.create_index([("order_id", ASCENDING)], name="idx_order_id")
        db.order_items.create_index([("product_id", ASCENDING)], name="idx_product_id")
        db.order_items.create_index([("deleted", ASCENDING)], name="idx_deleted")

        # Compound index for order + product lookups
        db.order_items.create_index([("order_id", ASCENDING), ("product_id", ASCENDING)], name="idx_order_product")
        print(f"{GREEN}✓ order_items indexes created{RESET}\n")

        # ===================================================================
        # Summary
        # ===================================================================
        print("\n" + "="*60)
        print("Index Creation Summary")
        print("="*60 + "\n")

        collections = [
            'stores', 'customers', 'categories', 'products',
            'product_embeddings', 'inventory', 'orders', 'order_items'
        ]

        for coll_name in collections:
            indexes = db[coll_name].list_indexes()
            index_list = list(indexes)
            print(f"{GREEN}{coll_name}: {len(index_list)} indexes{RESET}")
            for idx in index_list:
                keys = ', '.join([f"{k}: {v}" for k, v in idx.get('key', {}).items()])
                print(f"  - {idx.get('name', 'unnamed')}: {{ {keys} }}")
            print()

        print("="*60)
        print(f"{GREEN}All indexes created successfully!{RESET}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n{RED}✗ Error creating indexes: {e}{RESET}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == '__main__':
    main()
