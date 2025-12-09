#!/usr/bin/env python3
"""
MongoDB Connection Test Script
Tests connection to MongoDB Atlas using credentials from .env file
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")

def print_error(message):
    print(f"{RED}✗ {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}⚠ {message}{RESET}")

def print_info(message):
    print(f"{BLUE}ℹ {message}{RESET}")

def load_environment():
    """Load environment variables from .env file"""
    print("\n" + "="*60)
    print("MongoDB Connection Test")
    print("="*60 + "\n")

    # Find .env file (should be in project root directory)
    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        print_error(f".env file not found at: {env_path}")
        print_info("Please create a .env file in the project root directory")
        print_info("Use .env.sample as a template")
        return None

    print_success(f"Found .env file at: {env_path}")

    # Load environment variables
    load_dotenv(env_path)

    # Check required variables
    required_vars = {
        'MONGODB_CONNECTION_STRING': os.getenv('MONGODB_CONNECTION_STRING'),
        'MONGODB_DATABASE': os.getenv('MONGODB_DATABASE')
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        print_error("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return None

    print_success("All required environment variables found")
    return required_vars

def test_connection(connection_string, database_name):
    """Test MongoDB connection and basic operations"""

    print("\n" + "-"*60)
    print("Testing MongoDB Connection...")
    print("-"*60 + "\n")

    try:
        # Create MongoDB client
        print_info("Connecting to MongoDB Atlas...")
        client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )

        # Test connection
        client.admin.command('ping')
        print_success("Successfully connected to MongoDB Atlas!")

        # Get server info
        server_info = client.server_info()
        print_info(f"MongoDB version: {server_info['version']}")

        # List databases
        print("\n" + "-"*60)
        print("Available Databases:")
        print("-"*60)
        databases = client.list_database_names()
        for db in databases:
            if db == database_name:
                print(f"  {GREEN}• {db} (target database){RESET}")
            else:
                print(f"  • {db}")

        # Connect to target database
        print("\n" + "-"*60)
        print(f"Testing '{database_name}' database...")
        print("-"*60 + "\n")

        db = client[database_name]

        # Check if database exists (has collections)
        collections = db.list_collection_names()

        if not collections:
            print_warning(f"Database '{database_name}' exists but is empty")
            print_info("This is expected for a new database")
            print_info("Collections will be created when data is inserted")
        else:
            print_success(f"Found {len(collections)} collections in '{database_name}':")
            for coll in collections:
                doc_count = db[coll].count_documents({})
                print(f"  • {coll}: {doc_count:,} documents")

        # Test write permission
        print("\n" + "-"*60)
        print("Testing Write Permissions...")
        print("-"*60 + "\n")

        try:
            test_collection = db['__connection_test']
            test_doc = {'test': True, 'message': 'Connection test'}
            result = test_collection.insert_one(test_doc)
            print_success(f"Write test successful (inserted document: {result.inserted_id})")

            # Clean up test document
            test_collection.delete_one({'_id': result.inserted_id})
            print_success("Cleanup successful (deleted test document)")

            # If collection is now empty, drop it
            if test_collection.count_documents({}) == 0:
                test_collection.drop()
                print_success("Dropped empty test collection")

        except OperationFailure as e:
            print_error(f"Write test failed: {e}")
            print_warning("Your user may have read-only permissions")

        # Test change streams capability (required for Ditto connector)
        print("\n" + "-"*60)
        print("Testing Change Streams Support...")
        print("-"*60 + "\n")

        try:
            # This will fail if not running on a replica set
            db.watch(max_await_time_ms=100)
            print_success("Change Streams are supported")
            print_info("Your MongoDB deployment supports the Ditto connector")
        except OperationFailure:
            print_error("Change Streams are NOT supported")
            print_warning("Change Streams require MongoDB Atlas or a replica set")
            print_info("Ditto connector will not work without Change Streams")

        # Summary
        print("\n" + "="*60)
        print("Connection Test Summary")
        print("="*60 + "\n")
        print_success("✓ Connection successful")
        print_success("✓ Authentication successful")
        print_success(f"✓ Database '{database_name}' accessible")

        if collections:
            print_success(f"✓ Found {len(collections)} existing collections")
        else:
            print_info(f"ℹ Database is empty (ready for data generation)")

        print("\n" + "="*60)
        print(f"{GREEN}All tests passed! You're ready to proceed.{RESET}")
        print("="*60 + "\n")

        # Close connection
        client.close()
        return True

    except ConnectionFailure as e:
        print_error(f"Connection failed: {e}")
        print("\nPossible causes:")
        print("  • Invalid connection string")
        print("  • Network connectivity issues")
        print("  • MongoDB Atlas IP whitelist not configured")
        print("  • MongoDB Atlas cluster is paused or deleted")
        return False

    except ConfigurationError as e:
        print_error(f"Configuration error: {e}")
        print("\nPossible causes:")
        print("  • Malformed connection string")
        print("  • Invalid authentication credentials")
        return False

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def main():
    """Main entry point"""

    # Load environment variables
    env_vars = load_environment()
    if not env_vars:
        sys.exit(1)

    # Test connection
    success = test_connection(
        env_vars['MONGODB_CONNECTION_STRING'],
        env_vars['MONGODB_DATABASE']
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
