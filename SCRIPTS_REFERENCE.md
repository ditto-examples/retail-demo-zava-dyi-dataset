# Scripts Reference Guide

This document provides detailed information about all utility scripts in the project.

---

## Table of Contents

1. [Setup & Configuration](#setup--configuration)
2. [Data Management](#data-management)
3. [MongoDB Operations](#mongodb-operations)
4. [Ditto Connector](#ditto-connector)
5. [Testing & Verification](#testing--verification)

---

## Setup & Configuration

### encode_password.py

**Purpose**: URL-encode MongoDB passwords containing special characters

**Usage**:
```bash
python scripts/encode_password.py
# Or with password as argument
python scripts/encode_password.py "my@pass#word"
```

**When to use**:
- MongoDB connection string contains special characters (!@#$%^&*)
- Getting authentication errors with Atlas

**Output**:
```
Original password:  my@pass#word
Encoded password:   my%40pass%23word
```

### check_credentials.py

**Purpose**: Validate MongoDB connection string format and credentials

**Usage**:
```bash
python scripts/check_credentials.py
```

**Checks**:
- ✅ Connection string format
- ✅ Username/password presence
- ✅ Host format
- ✅ Special character encoding
- ⚠️ Common issues and fixes

**Output Example**:
```
Connection String Details:
------------------------------------------------------------
Username:  ditto-admin
Password:  ************ (15 characters)
Host:      ditto-demo.syetxyl.mongodb.net
Database:  (default)

Validation Checks:
------------------------------------------------------------
✓ No obvious issues detected
```

---

## Data Management

### generate_mongodb_data.py

**Purpose**: Generate complete retail dataset with realistic patterns

**Usage**:
```bash
# Generate with defaults (50k customers, 200k orders)
python scripts/generate_mongodb_data.py

# Or customize via .env
NUM_CUSTOMERS=100000
NUM_ORDERS=500000
python scripts/generate_mongodb_data.py
```

**What it generates**:
- 8 stores (7 physical + 1 online)
- 9 categories with seasonal multipliers
- 424 products with descriptions
- 424 product embeddings (separate collection)
- 50,000 customers (configurable)
- 3,168 inventory records
- 200,000 orders (configurable)
- ~450,000 order items

**Duration**: ~10 minutes for default dataset

**Features**:
- Realistic seasonal patterns
- Year-over-year growth (2022-2025)
- Weighted store distribution
- UUID-based inventory IDs
- CRDT-friendly data structures

### clear_mongodb_data.py

**Purpose**: Remove all data from collections for testing

**Usage**:
```bash
python scripts/clear_mongodb_data.py
```

**Safety Features**:
- ⚠️ Requires explicit confirmation: `DELETE ALL DATA`
- Shows exactly what will be deleted
- Preserves collection structure and indexes
- Cannot be undone

**What it does**:
- Deletes all documents from 8 collections
- Preserves indexes (44 indexes remain)
- Preserves change stream settings
- Verifies deletion completed

**What it does NOT do**:
- Does not drop collections
- Does not drop indexes
- Does not affect other databases
- Does not delete system collections

**Typical workflow**:
```bash
# Clear existing data
python scripts/clear_mongodb_data.py

# Regenerate with different settings
NUM_CUSTOMERS=10000 python scripts/generate_mongodb_data.py

# Verify new data
python scripts/test_connection.py
```

---

## MongoDB Operations

### create_indexes.py

**Purpose**: Create all MongoDB indexes for optimal query performance

**Usage**:
```bash
python scripts/create_indexes.py
```

**Creates**:
- 44 indexes across 8 collections
- Unique indexes for IDs and SKUs
- Compound indexes for common queries
- Text search indexes for products
- Location indexes for inventory

**Index Types**:
- Single field: `{ store_id: 1 }`
- Compound: `{ customer_id: 1, order_date: -1 }`
- Text search: `{ product_name: "text" }`
- Unique: `{ sku: 1 }` (unique: true)

**Duration**: ~5-10 seconds

**Idempotent**: Safe to run multiple times (indexes won't duplicate)

### drop_indexes.py

**Purpose**: Drop all custom indexes from collections (for schema changes)

**Usage**:
```bash
python scripts/drop_indexes.py
```

**Safety Features**:
- ⚠️ Requires explicit confirmation: `DROP INDEXES`
- Shows all indexes that will be dropped
- Preserves default `_id` indexes (cannot be dropped)
- Preserves change stream settings
- Does NOT affect collection data

**What it drops**:
- All custom indexes created by `create_indexes.py`
- Unique indexes, compound indexes, text search indexes
- ~43 custom indexes across 8 collections

**What it preserves**:
- Default `_id` index on each collection (8 indexes)
- Collection data (no documents deleted)
- Change stream pre/post image settings
- Collection structure

**When to use**:
- Data model has changed (new fields, different structure)
- Index strategy needs to be redesigned
- Testing different index configurations
- Migrating to a different schema

**Typical workflow**:
```bash
# 1. Drop old indexes
python scripts/drop_indexes.py

# 2. Update data model if needed
# (modify generate_mongodb_data.py or update existing data)

# 3. Update create_indexes.py with new index definitions
# (edit scripts/create_indexes.py)

# 4. Recreate indexes with new schema
python scripts/create_indexes.py

# 5. Verify
python scripts/test_connection.py
```

**Duration**: ~5-10 seconds

**Note**: After dropping indexes, query performance will degrade until indexes are recreated. Do this during maintenance windows.

### enable_change_streams.py

**Purpose**: Enable MongoDB Change Streams for Ditto connector

**Usage**:
```bash
python scripts/enable_change_streams.py
```

**Requirements**:
- MongoDB user with `dbAdmin` role
- MongoDB Atlas (M10+ cluster)
- MongoDB 4.4+

**What it enables**:
- Pre and post images on change streams
- Required for Ditto connector to see full document state

**Collections modified**:
- stores
- customers
- categories
- products
- inventory
- orders
- order_items

**Duration**: ~2-3 seconds

**Alternative methods**:
1. Via Atlas UI (if no dbAdmin role)
2. Via Atlas CLI (requires atlas CLI installed)

---

## Ditto Connector

### trigger_initial_sync.py

**Purpose**: Trigger initial sync of existing data to Ditto

**Usage**:
```bash
python scripts/trigger_initial_sync.py
```

**What it does**:
- Updates all documents with `_ditto_sync_triggered` timestamp
- Triggers MongoDB change streams
- Causes Ditto connector to sync existing data

**Safety Features**:
- ⚠️ Requires confirmation: `yes`
- Shows document counts before proceeding
- Updates in batches for large collections

**When to use**:
- After deploying Ditto connector
- After loading new data
- When existing data hasn't synced to Ditto

**Duration**: ~2-5 minutes for 200k orders

**Note**: Only needed ONCE after initial data load. New changes sync automatically.

---

## Testing & Verification

### test_connection.py

**Purpose**: Comprehensive MongoDB connection and setup verification

**Usage**:
```bash
python scripts/test_connection.py
```

**Tests**:
1. ✅ MongoDB connection
2. ✅ Database access
3. ✅ Collection listing
4. ✅ Document counts
5. ✅ Write permissions
6. ✅ Change streams support

**Output Example**:
```
Testing 'retail-demo' database...
------------------------------------------------------------

✓ Found 9 collections in 'retail-demo':
  • categories: 9 documents
  • stores: 8 documents
  • orders: 200,000 documents
  • order_items: 450,080 documents
  • customers: 50,000 documents
  • products: 424 documents
  • product_embeddings: 424 documents
  • inventory: 3,168 documents
```

**Duration**: ~5 seconds

### test_change_streams.py

**Purpose**: Verify change streams are enabled on all collections

**Usage**:
```bash
python scripts/test_change_streams.py
```

**Checks**:
- Change streams enabled status
- Pre/post images configuration
- Collection existence

**Output**:
```
✓ Change streams enabled on: stores
✓ Change streams enabled on: customers
✓ Change streams enabled on: categories
...
```

**When to use**:
- After running `enable_change_streams.py`
- Before deploying Ditto connector
- Troubleshooting sync issues

**Duration**: ~2 seconds

---

## Common Workflows

### Initial Setup

```bash
# 1. Configure environment
cp .env.sample .env
# Edit .env with your credentials

# 2. Test connection
python scripts/check_credentials.py
python scripts/test_connection.py

# 3. Generate data
python scripts/generate_mongodb_data.py

# 4. Create indexes
python scripts/create_indexes.py

# 5. Enable change streams (requires admin)
python scripts/enable_change_streams.py
python scripts/test_change_streams.py
```

### Reset and Reload Data

```bash
# 1. Clear existing data
python scripts/clear_mongodb_data.py

# 2. Regenerate with custom settings
NUM_CUSTOMERS=25000 NUM_ORDERS=100000 \
  python scripts/generate_mongodb_data.py

# 3. Verify
python scripts/test_connection.py
```

### Troubleshooting Connection Issues

```bash
# 1. Check credentials format
python scripts/check_credentials.py

# 2. Encode password if needed
python scripts/encode_password.py

# 3. Update .env with encoded password

# 4. Test connection
python scripts/test_connection.py
```

### Troubleshooting Sync Issues

```bash
# 1. Verify change streams
python scripts/test_change_streams.py

# 2. If not enabled, enable them
python scripts/enable_change_streams.py

# 3. Trigger initial sync
python scripts/trigger_initial_sync.py

# 4. Monitor connector logs
docker-compose logs -f ditto-connector
```

### Schema Migration (Data Model Changes)

```bash
# 1. Drop old indexes
python scripts/drop_indexes.py

# 2. Clear old data (optional)
python scripts/clear_mongodb_data.py

# 3. Update data generation script
# Edit scripts/generate_mongodb_data.py with new schema

# 4. Update index definitions
# Edit scripts/create_indexes.py with new indexes

# 5. Generate new data
python scripts/generate_mongodb_data.py

# 6. Create new indexes
python scripts/create_indexes.py

# 7. Verify everything works
python scripts/test_connection.py
```

---

## Environment Variables

All scripts use these environment variables from `.env`:

```bash
# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=retail-demo

# Ditto
DITTO_APP_ID=your_app_id
DITTO_API_KEY=your_api_key
DITTO_CLOUD_ENDPOINT=https://cloud.ditto.live

# Data Generation (optional)
NUM_CUSTOMERS=50000
NUM_ORDERS=200000
START_DATE=2022-01-01
END_DATE=2025-12-31
```

---

## Script Dependencies

All scripts require:
- Python 3.8+
- Virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Error Handling

### Common Errors

#### 1. "command not found: python"
```bash
# Use python3 instead
python3 scripts/test_connection.py
```

#### 2. "MONGODB_CONNECTION_STRING not found"
```bash
# Ensure .env file exists
ls -la .env

# Check .env has correct variable name
cat .env | grep MONGODB_CONNECTION_STRING
```

#### 3. "Permission denied: collMod"
```bash
# User needs dbAdmin role
# Grant in Atlas: Database Access → Edit User → Add dbAdmin role
# Or use Atlas UI to enable change streams manually
```

#### 4. "Authentication failed"
```bash
# Check credentials
python scripts/check_credentials.py

# Try encoding password
python scripts/encode_password.py
```

---

## Performance Tips

### Large Datasets

For datasets larger than default (50k customers, 200k orders):

```bash
# Increase batch sizes in generate_mongodb_data.py
BATCH_SIZE_CUSTOMERS=5000
BATCH_SIZE_ORDERS=10000

# Run with nohup to prevent interruption
nohup python scripts/generate_mongodb_data.py > generation.log 2>&1 &

# Monitor progress
tail -f generation.log
```

### Parallel Operations

Some scripts can run in parallel:

```bash
# Safe to run in parallel
python scripts/test_connection.py &
python scripts/check_credentials.py &

# DO NOT run these in parallel
# - generate_mongodb_data.py (creates data)
# - clear_mongodb_data.py (deletes data)
# - trigger_initial_sync.py (updates all documents)
```

---

## Security Notes

### Credential Safety

- ⚠️ Never commit `.env` file to git
- ⚠️ Use environment-specific credentials
- ⚠️ Rotate API keys regularly
- ⚠️ Use read-only users where possible

### Production Considerations

- Use separate databases for dev/staging/prod
- Limit `clear_mongodb_data.py` to dev/test environments
- Test scripts in staging before production
- Monitor script execution in production

---

## Additional Resources

- **MongoDB Documentation**: https://docs.mongodb.com/
- **Ditto Documentation**: https://docs.ditto.live/
- **Python MongoDB Driver**: https://pymongo.readthedocs.io/

---

**Last Updated**: 2024-12-07
