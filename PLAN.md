# Zava DIY Retail - MongoDB + Ditto Conversion Plan

**Status**: ✅ Phase 1 Complete | ⏭️ Phase 2 Ready to Start | Last Updated: 2025-12-05

## Project Overview

Convert the existing PostgreSQL-based Zava DIY retail demo application to MongoDB + Ditto for offline-first mobile and edge computing scenarios. This conversion will maintain all existing features while optimizing the data model for:
- MongoDB Atlas cloud database
- Ditto edge sync with CRDTs
- Mobile-first architecture (small documents, efficient sync)
- Realistic retail operations (inventory, orders, customers, products)

**Key Principle**: Keep original PostgreSQL code untouched. All new code lives in `conversion/` directory.

---

## Phase 1: Documentation & Design

### Step 1.1: Data Model Documentation
**File**: `conversion/docs/DATA_MODEL.md`

Document the complete MongoDB + Ditto data model including:
- [ ] Collection schemas with field definitions and types
- [ ] Relationship patterns (foreign keys, composite IDs)
- [ ] CRDT considerations (why no arrays, when to use MAPs)
- [ ] Ditto MongoDB Connector ID mappings for each collection
- [ ] Document size estimates
- [ ] Index strategies for MongoDB
- [ ] Query patterns for both MongoDB and Ditto

**Collections to document**:
- stores (8 documents)
- customers (50,000 documents)
- categories (9 documents)
- product_types (~30 documents)
- products (400 documents)
- product_embeddings (400 documents, MongoDB only - not synced to Ditto)
- inventory (3,000 documents with composite ID)
- orders (200,000 documents)
- order_items (200,000-500,000 documents with UUID)

### Step 1.2: Architecture Documentation
**File**: `conversion/docs/ARCHITECTURE.md`

Document the system architecture:
- [ ] MongoDB Atlas setup and configuration
- [ ] Ditto connector setup and configuration
- [ ] Data flow diagrams (mobile ↔ Ditto ↔ MongoDB)
- [ ] Sync strategies and subscriptions
- [ ] Security and access control patterns
- [ ] Offline-first considerations

### Step 1.3: Migration Guide
**File**: `conversion/docs/MIGRATION_GUIDE.md`

Document differences from PostgreSQL version:
- [ ] Schema changes (normalized to document-based)
- [ ] Query pattern changes (SQL → MongoDB/DQL)
- [ ] Why certain design decisions were made
- [ ] Trade-offs and limitations
- [ ] Comparison table: PostgreSQL vs MongoDB approach

---

## Phase 2: MongoDB Setup & Configuration

### Step 2.1: MongoDB Atlas Setup Script
**File**: `conversion/scripts/setup_mongodb_atlas.sh`

Create automated MongoDB Atlas setup:
- [ ] Atlas cluster creation (or connection to existing)
- [ ] Database creation: `zava`
- [ ] User creation with appropriate permissions
- [ ] Enable MongoDB Change Streams with pre/post images
- [ ] Connection string generation
- [ ] Environment variable setup

### Step 2.2: MongoDB Index Creation Script
**File**: `conversion/scripts/create_indexes.js`

MongoDB shell script to create all indexes:
- [ ] Primary indexes on all collections
- [ ] Foreign key indexes (customer_id, store_id, product_id, order_id)
- [ ] Text search indexes (product name/description)
- [ ] Vector search indexes (image_embedding, description_embedding)
- [ ] Composite indexes for common queries
- [ ] Index on soft delete flag

### Step 2.3: Environment Configuration Files
**Files**:
- `conversion/.env.sample` - Template with example variable names
- `conversion/.env` - Actual credentials (gitignored)

**Requirements**:
- [ ] All MongoDB connections MUST use .env file for credentials
- [ ] No hardcoded credentials in any script
- [ ] .env file must be in .gitignore
- [ ] .env.sample provided as template for users

**Environment Variables to Include**:

`.env.sample` template:
```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=zava
MONGODB_ATLAS_PROJECT_ID=your_project_id

# Ditto Configuration
DITTO_APP_ID=your_ditto_app_id
DITTO_API_KEY=your_ditto_api_key
DITTO_CLOUD_ENDPOINT=https://cloud.ditto.live

# Azure OpenAI (for embeddings)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-02-01

# Data Generation Settings
NUM_CUSTOMERS=50000
NUM_ORDERS=200000
START_DATE=2020-01-01
END_DATE=2026-12-31

# Optional: Local MongoDB (for testing)
MONGODB_LOCAL_CONNECTION_STRING=mongodb://localhost:27017/
```

**Usage Pattern in All Scripts**:
```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get MongoDB credentials
connection_string = os.getenv('MONGODB_CONNECTION_STRING')
database_name = os.getenv('MONGODB_DATABASE', 'zava')
```

---

## Phase 3: Data Generation

### Step 3.1: Core Data Generator
**File**: `conversion/scripts/generate_zava_mongodb.py`

Python script to generate complete dataset for MongoDB:
- [ ] **Load MongoDB credentials from .env file** (MONGODB_CONNECTION_STRING, MONGODB_DATABASE)
- [ ] Load reference data (stores, categories, product types)
- [ ] Load product data from JSON (with modifications)
- [ ] Generate customers (50,000) with Faker
- [ ] Generate products (400) with proper structure
- [ ] Generate inventory (store × product matrix, ~3,000 records)
- [ ] Generate orders (200,000) with seasonal patterns
- [ ] Generate order_items (separate collection, UUID-based)
- [ ] Handle embeddings in separate collection
- [ ] Add soft delete flags to all documents
- [ ] Duplicate ID fields for Ditto connector
- [ ] Batch insert optimization
- [ ] Progress reporting and error handling
- [ ] Connection pooling for performance

**Key differences from PostgreSQL version**:
- Use MongoDB document structure (not SQL tables)
- UUID generation for order_items
- Composite IDs for inventory
- Seasonal multipliers as MAP (not array)
- Separate embeddings collection
- Denormalized fields (customer names in orders, etc.)
- **All credentials from .env (no hardcoded connection strings)**

### Step 3.2: Reference Data Transformer
**File**: `conversion/scripts/transform_reference_data.py`

Transform existing `reference_data.json` for MongoDB:
- [ ] Convert to MongoDB document format
- [ ] Add duplicate ID fields
- [ ] Transform seasonal multipliers to MAP structure
- [ ] Output: `conversion/data/reference_data_mongodb.json`

### Step 3.3: Product Data Transformer
**File**: `conversion/scripts/transform_product_data.py`

Transform existing `product_data.json` for MongoDB:
- [ ] Split products from embeddings
- [ ] Generate proper document structure
- [ ] Add UUID/ID fields
- [ ] Output: `conversion/data/products_mongodb.json`
- [ ] Output: `conversion/data/embeddings_mongodb.json`

### Step 3.4: Data Generation Configuration
**File**: `conversion/config/generation_config.yaml`

YAML configuration for data generation:
- [ ] Number of customers (default: 50,000)
- [ ] Number of orders (default: 200,000)
- [ ] Date ranges (2020-2026)
- [ ] Store distribution weights
- [ ] Seasonal multipliers
- [ ] Growth factors by year

---

## Phase 4: Ditto Integration

### Step 4.1: Ditto Connector Configuration
**File**: `conversion/config/ditto_connector_config.yaml`

Ditto MongoDB Connector configuration:
- [ ] Collection mappings for each collection
- [ ] ID mapping strategies:
  - stores: single_field → store_id
  - customers: single_field → customer_id
  - categories: match_ids
  - products: single_field → product_id
  - inventory: match_ids (UUID)
  - orders: single_field → order_id
  - order_items: match_ids (UUID)
- [ ] Exclude product_embeddings from sync (too large)
- [ ] Change stream configuration
- [ ] Initial sync settings

### Step 4.2: Ditto Permission Rules
**File**: `conversion/config/ditto_permissions.json`

Ditto access control rules:
- [ ] Store-based access (replace PostgreSQL RLS)
- [ ] Read permissions by store_id
- [ ] Write permissions for inventory updates
- [ ] Admin/super-manager permissions

### Step 4.3: Ditto Query Examples
**File**: `conversion/examples/ditto_queries.md`

Document common Ditto queries:
- [ ] Get order with items (2-query pattern)
- [ ] Get inventory for store
- [ ] Search products by name
- [ ] Customer order history
- [ ] Subscription patterns for offline sync

---

## Phase 5: Query & Access Patterns

### Step 5.1: MongoDB Query Examples
**File**: `conversion/examples/mongodb_queries.js`

MongoDB shell examples:
- [ ] Order with items (aggregation $lookup)
- [ ] Customer analytics
- [ ] Inventory reports
- [ ] Product search (text search)
- [ ] Vector similarity search (embeddings)
- [ ] Sales analytics by date range
- [ ] Top products by category

### Step 5.2: Python MongoDB Client Examples
**File**: `conversion/examples/mongodb_client.py`

Python code examples using PyMongo:
- [ ] **Connection setup using .env credentials**
- [ ] CRUD operations
- [ ] Aggregation pipelines
- [ ] Vector search with embeddings
- [ ] Batch operations
- [ ] Error handling and retry logic

### Step 5.3: MCP Server Updates
**Files**:
- `conversion/src/mcp_server/customer_sales_mongodb.py`
- `conversion/src/mcp_server/sales_analysis_mongodb.py`

Update existing MCP servers for MongoDB:
- [ ] **Replace PostgreSQL connection with MongoDB using .env credentials**
- [ ] Update queries from SQL to MongoDB aggregation
- [ ] Handle composite IDs
- [ ] Update vector search for separate embeddings collection
- [ ] Test with Claude Code integration
- [ ] Add connection pooling
- [ ] Implement proper error handling

---

## Phase 6: Utilities & Tools

### Step 6.1: Product Management Tools
**File**: `conversion/scripts/add_product_mongodb.py`

Interactive tool to add products:
- [ ] **Use .env for MongoDB credentials**
- [ ] Add product to products collection
- [ ] Generate/add embeddings to embeddings collection
- [ ] Initialize inventory across stores
- [ ] Validate SKU uniqueness

### Step 6.2: Data Validation Script
**File**: `conversion/scripts/validate_data.py`

Comprehensive validation of generated data in MongoDB:
- [ ] **Use .env for MongoDB connection credentials**
- [ ] Count documents in each collection (match expected counts)
- [ ] Verify composite IDs are unique
- [ ] Check foreign key references exist (customer_id, store_id, product_id, order_id)
- [ ] Validate date ranges (2020-2026)
- [ ] Check for missing required fields
- [ ] Verify soft delete flags exist on all documents
- [ ] Test index coverage and usage
- [ ] Validate document structure (all required fields present)
- [ ] Check data types are correct (strings, numbers, dates, booleans)
- [ ] Verify UUID format for order_items
- [ ] Validate composite ID structure for inventory
- [ ] Check denormalized fields match source (customer_name in orders matches customers collection)
- [ ] Verify seasonal multipliers are MAPs not arrays
- [ ] Validate embedding dimensions (512 for images, 1536 for descriptions)
- [ ] Check for orphaned records (order_items without matching orders)
- [ ] Generate validation report with pass/fail status

### Step 6.3: Data Export/Import Tools
**File**: `conversion/scripts/export_import.py`

Tools for data portability:
- [ ] **Use .env for MongoDB credentials**
- [ ] Export collections to JSON
- [ ] Import from JSON to MongoDB
- [ ] Backup/restore functionality
- [ ] mongodump/mongorestore wrapper scripts

### Step 6.4: Embedding Generation Tools
**File**: `conversion/scripts/generate_embeddings_mongodb.py`

Generate embeddings for products:
- [ ] **Use .env for MongoDB and Azure OpenAI credentials**
- [ ] Image embedding generation (OpenAI CLIP)
- [ ] Description embedding generation (Azure OpenAI)
- [ ] Batch processing
- [ ] Update embeddings collection
- [ ] Progress tracking
- [ ] Error handling and retry logic

---

## Phase 7: Testing & Validation

### Step 7.1: Unit Tests
**File**: `conversion/tests/test_data_generation.py`

Test data generation logic:
- [ ] Test document structure generation
- [ ] Test UUID generation
- [ ] Test composite ID generation
- [ ] Test date range validation
- [ ] Test seasonal multiplier calculations
- [ ] Test .env file loading
- [ ] Test error handling for missing environment variables

### Step 7.2: Data Validation Tests
**File**: `conversion/tests/test_data_validation.py`

**Critical**: Comprehensive tests to validate ALL data is correctly stored in MongoDB:

**Collection Count Validation**:
- [ ] Test stores collection has exactly 8 documents
- [ ] Test customers collection has ~50,000 documents
- [ ] Test categories collection has exactly 9 documents
- [ ] Test product_types collection has ~30 documents
- [ ] Test products collection has exactly 400 documents
- [ ] Test product_embeddings collection has exactly 400 documents
- [ ] Test inventory collection has ~3,000 documents
- [ ] Test orders collection has ~200,000 documents
- [ ] Test order_items collection has 200,000-500,000 documents

**Document Structure Validation**:
- [ ] Test all stores have required fields (store_id, store_name, is_online, location, deleted)
- [ ] Test all customers have required fields (customer_id, first_name, last_name, email, phone, primary_store_id, deleted)
- [ ] Test all categories have required fields (category_id, category_name, seasonal_multipliers, deleted)
- [ ] Test all products have required fields (product_id, sku, product_name, category_id, cost, base_price, deleted)
- [ ] Test all product_embeddings have both image_embedding and description_embedding
- [ ] Test all inventory docs have composite _id with store_id and product_id
- [ ] Test all orders have required fields (order_id, customer_id, store_id, order_date, deleted)
- [ ] Test all order_items have required fields (UUID _id, order_id, product_id, quantity, unit_price, deleted)

**Data Type Validation**:
- [ ] Test UUIDs are valid format
- [ ] Test dates are in ISO 8601 format
- [ ] Test prices are Decimal/float with 2 decimal places
- [ ] Test quantities are positive integers
- [ ] Test booleans are true/false (deleted, is_online)
- [ ] Test embeddings are arrays of correct length (512 or 1536)

**Foreign Key Validation**:
- [ ] Test all customer.primary_store_id references exist in stores
- [ ] Test all product.category_id references exist in categories
- [ ] Test all inventory.store_id references exist in stores
- [ ] Test all inventory.product_id references exist in products
- [ ] Test all order.customer_id references exist in customers
- [ ] Test all order.store_id references exist in stores
- [ ] Test all order_item.order_id references exist in orders
- [ ] Test all order_item.product_id references exist in products

**Data Integrity Validation**:
- [ ] Test no orphaned order_items (all have valid order_id)
- [ ] Test composite IDs are unique (inventory)
- [ ] Test UUIDs are unique (order_items)
- [ ] Test SKUs are unique (products)
- [ ] Test emails are unique (customers)
- [ ] Test seasonal multipliers are MAPs not arrays (12 keys: jan-dec)
- [ ] Test all documents have deleted=false initially
- [ ] Test denormalized data matches (customer_name in orders matches customers.first_name + last_name)

**Business Logic Validation**:
- [ ] Test order dates are between 2020-2026
- [ ] Test customer created_at dates are reasonable
- [ ] Test gross margins are 33%
- [ ] Test order totals = sum of line_total from order_items
- [ ] Test order.item_count matches number of order_items for that order
- [ ] Test inventory stock_level is non-negative

**Index Validation**:
- [ ] Test indexes exist on all foreign key fields
- [ ] Test composite indexes exist (inventory)
- [ ] Test text search indexes exist (product_name, product_description)
- [ ] Test vector search indexes exist (embeddings)
- [ ] Test unique indexes on SKU, email

**Report Generation**:
- [ ] Generate detailed validation report (pass/fail for each test)
- [ ] Log any data inconsistencies found
- [ ] Provide summary statistics (document counts, data quality score)

### Step 7.3: Integration Tests
**File**: `conversion/tests/test_mongodb_integration.py`

Test MongoDB operations:
- [ ] **Test connection using .env credentials**
- [ ] Test CRUD operations
- [ ] Test aggregations
- [ ] Test index usage with explain()
- [ ] Test vector search queries
- [ ] Test query performance on large collections

### Step 7.4: Ditto Sync Tests
**File**: `conversion/tests/test_ditto_sync.py`

Test Ditto connector:
- [ ] **Use .env for Ditto credentials**
- [ ] Test document sync from MongoDB → Ditto
- [ ] Test document sync from Ditto → MongoDB
- [ ] Test composite ID handling
- [ ] Test conflict resolution
- [ ] Test subscription filters
- [ ] Test that product_embeddings are NOT synced to Ditto

### Step 7.5: Performance Tests
**File**: `conversion/tests/test_performance.py`

Benchmark key operations:
- [ ] Query performance (MongoDB vs PostgreSQL baseline)
- [ ] Sync performance (document sizes, counts)
- [ ] Index effectiveness (query plans)
- [ ] Aggregation pipeline performance
- [ ] Bulk insert performance

---

## Phase 8: Deployment & Documentation

### Step 8.1: Docker Compose Setup
**File**: `conversion/docker-compose.yml`

Local development environment:
- [ ] MongoDB container (or Atlas connection)
- [ ] Ditto server (if self-hosted)
- [ ] MCP server containers
- [ ] Volume mounts for data persistence

### Step 8.2: Deployment Guide
**File**: `conversion/docs/DEPLOYMENT.md`

Step-by-step deployment instructions:
- [ ] MongoDB Atlas setup
- [ ] Ditto Cloud setup
- [ ] MongoDB Connector configuration
- [ ] Data generation and loading
- [ ] Index creation
- [ ] Validation steps
- [ ] Troubleshooting common issues

### Step 8.3: Quick Start Guide
**File**: `conversion/README.md`

User-friendly getting started guide:
- [ ] Prerequisites (Python, MongoDB, Ditto account)
- [ ] Installation steps
- [ ] Configuration (environment variables)
- [ ] Run data generation
- [ ] Verify setup
- [ ] Example queries
- [ ] Next steps

### Step 8.4: API Documentation
**File**: `conversion/docs/API.md`

Document all scripts and their usage:
- [ ] generate_zava_mongodb.py options
- [ ] Environment variables
- [ ] Configuration files
- [ ] Utility scripts
- [ ] Error codes and troubleshooting

---

## Phase 9: Comparison & Analysis

### Step 9.1: Feature Comparison
**File**: `conversion/docs/COMPARISON.md`

Compare PostgreSQL vs MongoDB+Ditto implementations:
- [ ] Feature parity checklist
- [ ] Query pattern differences
- [ ] Performance characteristics
- [ ] Storage requirements
- [ ] Sync capabilities
- [ ] Offline-first benefits
- [ ] When to use each approach

### Step 9.2: Demo Scenarios
**File**: `conversion/docs/DEMO_SCENARIOS.md`

Document demo use cases focused on inventory tracking:

**Worker App** (Store Employee):
- [ ] Find product location in store (aisle/shelf lookup)
- [ ] Check inventory levels in real-time
- [ ] Receive low stock alerts (reorder thresholds)
- [ ] Move inventory between stores (transfer workflow)
- [ ] Order items from warehouse to store
- [ ] Update inventory after receiving shipment
- [ ] Perform physical inventory counts
- [ ] Track inventory changes after orders (dynamic updates)

**Sales Rep App** (Customer-focused):
- [ ] Browse product catalog offline
- [ ] Check product availability across stores
- [ ] View customer order history
- [ ] Create orders (with automatic inventory decrement)
- [ ] Customer lookup and management
- [ ] View real-time inventory to avoid overselling

**Offline-First Scenarios**:
- [ ] Worker uses app offline, syncs when back online
- [ ] Multiple workers update different products simultaneously (CRDT conflict-free)
- [ ] Order placed → inventory dynamically updates across all devices
- [ ] Low stock alerts appear in real-time on worker devices

**Conflict Resolution**:
- [ ] Two workers update same inventory item (last-write-wins on stock_level)
- [ ] Worker moves items while another worker does physical count (CRDT merge)

---

## Phase 10: Final Polish

### Step 10.1: Code Review Checklist
**File**: `conversion/docs/CODE_REVIEW.md`

Ensure code quality:
- [ ] All scripts have error handling
- [ ] All functions have docstrings
- [ ] **All MongoDB connections use .env (NO hardcoded credentials)**
- [ ] **All scripts load dotenv and check for required environment variables**
- [ ] Configuration is externalized
- [ ] Secrets are not hardcoded anywhere
- [ ] Code follows Python best practices (PEP 8)
- [ ] Dependencies are documented (requirements.txt)
- [ ] .env.sample is complete and up-to-date

### Step 10.2: Documentation Review
- [ ] All markdown files are properly formatted
- [ ] Code examples are tested and working
- [ ] Links between documents are valid
- [ ] Terminology is consistent
- [ ] Diagrams are clear (if added)

### Step 10.3: Repository Preparation
**File**: `conversion/.gitignore`

Prepare for GitHub:
- [ ] **Ignore .env file (CRITICAL - contains secrets)**
- [ ] **Include .env.sample (template, no secrets)**
- [ ] Ignore generated data files (*.json in data/)
- [ ] Ignore Python cache (__pycache__, *.pyc, *.pyo)
- [ ] Ignore virtual environments (venv/, env/, .venv/)
- [ ] Ignore OS-specific files (.DS_Store, Thumbs.db)
- [ ] Ignore IDE files (.vscode/, .idea/, *.swp)
- [ ] Ignore test output and logs (*.log, test-results/)

**Example .gitignore**:
```gitignore
# Environment variables (NEVER commit .env)
.env

# Generated data files
data/*.json
data/*.csv
*.backup

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Virtual environments
venv/
env/
.venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs and test output
*.log
test-results/
.pytest_cache/
```

**File**: `conversion/LICENSE`
- [ ] Choose appropriate license

**File**: `conversion/CONTRIBUTING.md`
- [ ] Guidelines for contributions

---

## File Structure Summary

```
conversion/
├── PLAN.md                          # This file
├── Claude.md                        # Summary of research and decisions
├── README.md                        # Quick start guide
├── LICENSE
├── .gitignore                       # Ignore .env, cache, data files
├── .env.sample                      # Environment variable template (COMMITTED)
├── .env                             # Actual credentials (GITIGNORED)
├── requirements.txt                 # Python dependencies
│
├── config/
│   ├── generation_config.yaml      # Data generation settings
│   ├── ditto_connector_config.yaml # Ditto MongoDB Connector config
│   └── ditto_permissions.json      # Ditto access control rules
│
├── docs/
│   ├── ARCHITECTURE.md              # System architecture
│   ├── DATA_MODEL.md                # Complete schema documentation
│   ├── MIGRATION_GUIDE.md           # PostgreSQL → MongoDB guide
│   ├── DEPLOYMENT.md                # Deployment instructions
│   ├── API.md                       # Script/API documentation
│   ├── COMPARISON.md                # PostgreSQL vs MongoDB+Ditto
│   ├── DEMO_SCENARIOS.md            # Demo use cases
│   └── CODE_REVIEW.md               # Quality checklist
│
├── scripts/
│   ├── setup_mongodb_atlas.sh      # Atlas setup automation
│   ├── create_indexes.js            # MongoDB index creation
│   ├── generate_zava_mongodb.py    # Main data generator
│   ├── transform_reference_data.py # Transform reference JSON
│   ├── transform_product_data.py   # Transform product JSON
│   ├── add_product_mongodb.py      # Add single product
│   ├── validate_data.py             # Data validation
│   ├── export_import.py             # Backup/restore tools
│   └── generate_embeddings_mongodb.py # Embedding generation
│
├── data/
│   ├── reference_data_mongodb.json  # Transformed reference data
│   ├── products_mongodb.json        # Transformed product data
│   └── embeddings_mongodb.json      # Separated embeddings
│
├── src/
│   └── mcp_server/
│       ├── customer_sales_mongodb.py    # MCP server for product search
│       └── sales_analysis_mongodb.py    # MCP server for analytics
│
├── examples/
│   ├── ditto_queries.md             # Ditto query examples
│   ├── mongodb_queries.js           # MongoDB shell examples
│   └── mongodb_client.py            # Python client examples
│
├── tests/
│   ├── test_data_generation.py      # Unit tests
│   ├── test_data_validation.py      # Data validation tests (CRITICAL)
│   ├── test_mongodb_integration.py  # Integration tests
│   ├── test_ditto_sync.py           # Ditto sync tests
│   └── test_performance.py          # Performance benchmarks
│
└── docker-compose.yml               # Local development setup
```

---

## Dependencies

### Python Packages
**File**: `conversion/requirements.txt`
```
pymongo>=4.6.0              # MongoDB driver
motor>=3.3.0                # Async MongoDB driver
faker>=20.0.0               # Fake data generation
python-dotenv>=1.0.0        # Environment variables
pyyaml>=6.0                 # YAML configuration
openai>=1.0.0               # OpenAI embeddings
azure-identity>=1.15.0      # Azure auth
pytest>=7.4.0               # Testing
pytest-asyncio>=0.21.0      # Async testing
```

### System Requirements
- Python 3.10+
- MongoDB Atlas account (or local MongoDB 7.0+)
- Ditto Cloud account
- Azure OpenAI access (for embeddings)
- Git

---

## Execution Order

For someone implementing this plan, execute phases in order:

1. **Phase 1** (Documentation) → Design and document everything first
2. **Phase 2** (MongoDB Setup) → Set up infrastructure
3. **Phase 3** (Data Generation) → Generate the dataset
4. **Phase 4** (Ditto Integration) → Configure Ditto connector
5. **Phase 5** (Query Patterns) → Implement access patterns
6. **Phase 6** (Utilities) → Build supporting tools
7. **Phase 7** (Testing) → Validate everything works
8. **Phase 8** (Deployment) → Document production deployment
9. **Phase 9** (Comparison) → Analyze and compare approaches
10. **Phase 10** (Polish) → Final review and cleanup

---

## Success Criteria

The conversion is complete when:
- [ ] **.env.sample file created with all required environment variables**
- [ ] **All scripts use .env for credentials (no hardcoded values)**
- [ ] **.env is in .gitignore**
- [ ] All 200K+ documents generated and loaded into MongoDB Atlas
- [ ] **All data validation tests pass (test_data_validation.py)**
- [ ] Document counts match expected (stores: 8, customers: 50K, orders: 200K, etc.)
- [ ] Foreign key references validated
- [ ] Indexes created and validated
- [ ] Ditto MongoDB Connector syncing successfully
- [ ] product_embeddings collection NOT synced to Ditto (confirmed)
- [ ] All queries (MongoDB and Ditto) return correct results
- [ ] Vector search working for product embeddings
- [ ] MCP servers functioning with MongoDB backend
- [ ] Documentation is complete and accurate
- [ ] All tests are passing (unit, integration, validation, performance)
- [ ] Demo scenarios work end-to-end
- [ ] Code review checklist completed
- [ ] Ready to move to standalone GitHub repository

---

## Timeline Estimate

- **Phase 1**: 2-3 days (documentation and design)
- **Phase 2**: 1-2 days (MongoDB setup including .env.sample creation)
- **Phase 3**: 3-4 days (data generation scripts with .env integration)
- **Phase 4**: 1-2 days (Ditto configuration)
- **Phase 5**: 2 days (query patterns and MCP servers)
- **Phase 6**: 2 days (utilities including comprehensive validation script)
- **Phase 7**: 3-4 days (testing - includes comprehensive data validation tests)
- **Phase 8**: 1 day (deployment docs)
- **Phase 9**: 1 day (comparison and analysis)
- **Phase 10**: 1 day (polish and security review)

**Total**: 17-23 days for complete implementation

**Note**: Phase 7 (Testing) is critical and includes comprehensive data validation that must pass before moving to production.

---

## Notes & Considerations

### Security & Credentials (CRITICAL)
- **ALL scripts MUST use .env file for MongoDB credentials**
- **NEVER hardcode connection strings, API keys, or passwords**
- **.env file MUST be in .gitignore**
- **.env.sample provided as template (no actual credentials)**
- **All code should validate required environment variables on startup**
- **Use python-dotenv library to load environment variables**
- **Scripts should fail fast with clear error if .env is missing or incomplete**

**Example validation pattern**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = ['MONGODB_CONNECTION_STRING', 'MONGODB_DATABASE']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        f"Please create a .env file based on .env.sample"
    )
```

### CRDT Best Practices
- No arrays for concurrent updates (use MAPs or separate collections)
- Duplicate ID fields in document body for Ditto queries
- Soft deletes instead of hard deletes
- Bounded document sizes (<100KB typical, <500KB max)

### MongoDB Connector Constraints
- Only top-level fields in ID mappings
- ID fields must be immutable and always present
- Enable Change Streams with pre/post images
- Collections must exist before connector setup

### Offline-First Optimizations
- Separate large embeddings from main product collection
- Use subscription filters to sync only relevant data
- Small document sizes for efficient mobile sync
- Denormalize frequently accessed fields

### Data Validation Requirements
- Run comprehensive validation tests after data generation
- Validate ALL collections have expected document counts
- Verify foreign key references exist
- Check document structure matches schema
- Validate data types (UUIDs, dates, prices, etc.)
- Test indexes exist and are being used
- Generate validation report with pass/fail status

### Future Enhancements (Post-MVP)
- Real-time dashboard
- Mobile app examples (iOS/Android)
- Conflict resolution UI
- Performance monitoring
- Advanced analytics queries
- Multi-region deployment guide
