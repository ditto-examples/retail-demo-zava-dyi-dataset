# Migration Guide: PostgreSQL to MongoDB + Ditto

This document guides you through converting the Zava DIY Retail application from PostgreSQL to MongoDB + Ditto, highlighting key differences, design decisions, and migration strategies.

---

## Table of Contents
1. [Overview](#overview)
2. [Schema Changes](#schema-changes)
3. [Query Pattern Changes](#query-pattern-changes)
4. [Design Decision Rationale](#design-decision-rationale)
5. [Trade-offs & Limitations](#trade-offs--limitations)
6. [Migration Steps](#migration-steps)
7. [Comparison Tables](#comparison-tables)

---

## Overview

### Why Migrate?

**From**: PostgreSQL (cloud-only, always-online)
**To**: MongoDB + Ditto (offline-first, edge computing)

**Goals**:
- Enable offline CRUD operations on mobile devices
- Support peer-to-peer sync between devices
- Automatic conflict resolution (CRDTs)
- Flexible schema evolution
- Horizontal scalability

**Not Changing**:
- Core business logic (orders, inventory, customers)
- Data relationships (stores → orders → items)
- Seasonal patterns and growth factors
- AI embeddings for search

---

## Schema Changes

### 1. Relational Tables → Document Collections

**PostgreSQL**: 10 normalized tables with foreign keys
**MongoDB**: 9 collections with referenced IDs

| PostgreSQL Table | MongoDB Collection | Change |
|------------------|-------------------|---------|
| retail.stores | stores | Direct mapping |
| retail.customers | customers | Direct mapping |
| retail.categories | categories | **Seasonal multipliers: array → MAP** |
| retail.product_types | product_types | Direct mapping |
| retail.products | products | **Specifications as MAP** |
| retail.product_image_embeddings | product_embeddings | **Combined with description embeddings** |
| retail.product_description_embeddings | ↑ (merged) | ↑ (merged into one collection) |
| retail.inventory | inventory | **Composite _id: {store_id, product_id}** |
| retail.orders | orders | **Denormalized fields added** |
| retail.order_items | order_items | **UUID _id instead of SERIAL** |

### 2. Key Schema Transformations

#### Seasonal Multipliers: Array → MAP

**PostgreSQL** (array):
```sql
CREATE TABLE retail.categories (
  category_id SERIAL PRIMARY KEY,
  category_name TEXT,
  seasonal_multipliers DECIMAL[] -- [0.8, 0.9, 1.2, ...]
);
```

**MongoDB** (MAP):
```json
{
  "_id": "cat_power_tools",
  "category_id": "cat_power_tools",
  "seasonal_multipliers": {
    "jan": 0.8,
    "feb": 0.9,
    "mar": 1.2,
    ...
  }
}
```

**Reason**: CRDT compatibility. MAPs allow independent updates (Device A updates `jan`, Device B updates `feb` → both merge successfully). Arrays are last-write-wins (conflict).

#### Embeddings: Separate Tables → Single Collection

**PostgreSQL** (2 tables):
```sql
CREATE TABLE retail.product_image_embeddings (
  product_id INTEGER PRIMARY KEY,
  image_embedding vector(512)
);

CREATE TABLE retail.product_description_embeddings (
  product_id INTEGER PRIMARY KEY,
  description_embedding vector(1536)
);
```

**MongoDB** (1 collection):
```json
{
  "_id": "prod_drill_001",
  "product_id": "prod_drill_001",
  "image_embedding": [...512 floats...],
  "description_embedding": [...1536 floats...]
}
```

**Reason**: Simpler data model. Both embeddings belong to same product. MongoDB collection NOT synced to Ditto (too large for mobile).

#### Inventory: Composite Primary Key

**PostgreSQL**:
```sql
CREATE TABLE retail.inventory (
  store_id INTEGER,
  product_id INTEGER,
  stock_level INTEGER,
  PRIMARY KEY (store_id, product_id)
);
```

**MongoDB**:
```json
{
  "_id": {
    "store_id": "store_seattle",
    "product_id": "prod_drill_001"
  },
  "store_id": "store_seattle",      // Duplicated for Ditto queries
  "product_id": "prod_drill_001",  // Duplicated for Ditto queries
  "stock_level": 50
}
```

**Reason**: Natural key. Ditto composite ID mapping. Each store-product pair updates independently (CRDT isolation).

#### Order Items: SERIAL → UUID

**PostgreSQL**:
```sql
CREATE TABLE retail.order_items (
  order_item_id SERIAL PRIMARY KEY,
  order_id INTEGER,
  product_id INTEGER,
  ...
);
```

**MongoDB**:
```json
{
  "_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID
  "order_id": "order_20251205_001",
  "product_id": "prod_drill_001",
  ...
}
```

**Reason**: No sequence management needed. UUIDs work offline (no central sequence generator). Simple 1:1 mapping with Ditto.

#### Orders: Added Denormalized Fields

**PostgreSQL**:
```sql
CREATE TABLE retail.orders (
  order_id SERIAL PRIMARY KEY,
  customer_id INTEGER,
  store_id INTEGER,
  order_date DATE
  -- NO customer/store names
);
```

**MongoDB**:
```json
{
  "_id": "order_20251205_001",
  "customer_id": "cust_123",
  "store_id": "store_seattle",
  "order_date": "2025-01-15T10:30:00Z",

  // Denormalized for offline display
  "customer_name": "John Smith",
  "customer_email": "john@email.com",
  "store_name": "Zava Retail Seattle"
}
```

**Reason**: Offline-first. Display order without querying customers/stores collections. Historical snapshot (customer name changes don't affect old orders).

### 3. Soft Deletes

**PostgreSQL**:
```sql
DELETE FROM retail.products WHERE product_id = 123;
```

**MongoDB**:
```json
{
  "_id": "prod_123",
  "deleted": true,
  "deleted_at": "2024-12-05T10:00:00Z"
}
```

**Queries always filter**:
```javascript
db.products.find({ deleted: false })
```

**Reason**: Ditto connector requirement. MongoDB deletions "win" over Ditto changes (data loss risk). Soft deletes preserve audit trail.

### 4. ID Field Duplication

**PostgreSQL** (single ID):
```sql
CREATE TABLE retail.customers (
  customer_id SERIAL PRIMARY KEY,
  ...
);
```

**MongoDB** (duplicate IDs):
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "customer_id": "cust_123",  // Duplicated for Ditto
  ...
}
```

**Reason**: Ditto connector requirement. Needs top-level field for ID mapping. Enables Ditto queries like `WHERE customer_id = 'cust_123'`.

---

## Query Pattern Changes

### 1. Joins → Application-Level or $lookup

**PostgreSQL** (JOIN):
```sql
SELECT o.*, c.first_name, c.last_name
FROM retail.orders o
JOIN retail.customers c ON o.customer_id = c.customer_id
WHERE o.order_id = 'order_123';
```

**MongoDB** ($lookup aggregation):
```javascript
db.orders.aggregate([
  { $match: { order_id: "order_123" } },
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "customer_id",
      as: "customer"
    }
  },
  { $unwind: "$customer" }
])
```

**MongoDB** (denormalized, no join needed):
```javascript
db.orders.findOne({ order_id: "order_123" })
// Returns: { order_id, customer_name, customer_email, ... }
```

**Ditto** (2 queries, using DQL):
```swift
// Query 1: Get order
let orderResult = await ditto.store.execute(
  query: "SELECT * FROM orders WHERE _id = :orderId",
  arguments: ["orderId": "order_123"]
)
let order = orderResult.items.first

// Query 2: Get customer (if needed)
let customerResult = await ditto.store.execute(
  query: "SELECT * FROM customers WHERE customer_id = :customerId",
  arguments: ["customerId": order.value["customer_id"].stringValue]
)
let customer = customerResult.items.first
```

### 2. Foreign Key Constraints → Application Validation

**PostgreSQL** (enforced by DB):
```sql
ALTER TABLE retail.orders
  ADD CONSTRAINT fk_customer
  FOREIGN KEY (customer_id) REFERENCES retail.customers(customer_id);

-- Attempting to insert invalid customer_id → ERROR
```

**MongoDB** (application-level):
```python
# Validate customer exists before creating order
customer = db.customers.find_one({"customer_id": order_data["customer_id"]})
if not customer:
    raise ValueError(f"Customer {order_data['customer_id']} not found")

# Insert order
db.orders.insert_one(order_data)
```

### 3. Transactions

**PostgreSQL** (ACID across tables):
```sql
BEGIN;
  INSERT INTO retail.orders (...) VALUES (...);
  INSERT INTO retail.order_items (...) VALUES (...);
  UPDATE retail.inventory SET stock_level = stock_level - 1 WHERE ...;
COMMIT;
```

**MongoDB** (transactions within database):
```javascript
const session = client.startSession();
session.startTransaction();

try {
  await db.orders.insertOne(order, { session });
  await db.order_items.insertMany(items, { session });
  await db.inventory.updateOne(
    { "_id": { store_id, product_id } },
    { $inc: { stock_level: -1 } },
    { session }
  );
  await session.commitTransaction();
} catch (error) {
  await session.abortTransaction();
  throw error;
} finally {
  await session.endSession();
}
```

**Ditto** (CRDT eventual consistency using DQL):
```swift
// No traditional transactions
// CRDTs ensure eventual consistency across peers

// Create order (eventually consistent)
await ditto.store.execute(
  query: "INSERT INTO orders DOCUMENTS (:order)",
  arguments: ["order": order]
)

// Create items (eventually consistent)
for item in items {
  await ditto.store.execute(
    query: "INSERT INTO order_items DOCUMENTS (:item)",
    arguments: ["item": item]
  )
}

// Update inventory (CRDT merge, no conflicts)
await ditto.store.execute(
  query: """
    UPDATE inventory
    SET stock_level = stock_level - 1
    WHERE store_id = :storeId AND product_id = :productId
  """,
  arguments: [
    "storeId": "store_seattle",
    "productId": "prod_123"
  ]
)
```

### 4. Aggregations

**PostgreSQL**:
```sql
SELECT
  c.category_name,
  COUNT(*) as order_count,
  SUM(oi.quantity) as total_units,
  SUM(oi.line_total) as revenue
FROM retail.orders o
JOIN retail.order_items oi ON o.order_id = oi.order_id
JOIN retail.products p ON oi.product_id = p.product_id
JOIN retail.categories c ON p.category_id = c.category_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.category_name
ORDER BY revenue DESC;
```

**MongoDB**:
```javascript
db.order_items.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "order_id",
      foreignField: "order_id",
      as: "order"
    }
  },
  { $unwind: "$order" },
  { $match: { "order.order_date": { $gte: ISODate("2024-01-01") } } },
  {
    $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "product_id",
      as: "product"
    }
  },
  { $unwind: "$product" },
  {
    $lookup: {
      from: "categories",
      localField: "product.category_id",
      foreignField: "category_id",
      as: "category"
    }
  },
  { $unwind: "$category" },
  {
    $group: {
      _id: "$category.category_name",
      order_count: { $sum: 1 },
      total_units: { $sum: "$quantity" },
      revenue: { $sum: "$line_total" }
    }
  },
  { $sort: { revenue: -1 } }
])
```

**Ditto** (limited aggregations, using DQL):
```swift
// Simple queries work
let result = await ditto.store.execute(
  query: "SELECT * FROM orders WHERE order_date >= :startDate",
  arguments: ["startDate": "2024-01-01"]
)
let orders = result.items

// Complex aggregations → compute in app code
let revenue = orders.reduce(0) { $0 + $1.value["total"].doubleValue }
```

### 5. Full-Text Search

**PostgreSQL**:
```sql
SELECT * FROM retail.products
WHERE to_tsvector('english', product_name || ' ' || product_description)
      @@ to_tsquery('english', 'cordless & drill');
```

**MongoDB** (text index):
```javascript
// Create text index
db.products.createIndex({
  product_name: "text",
  product_description: "text"
})

// Query
db.products.find({
  $text: { $search: "cordless drill" }
})
```

**Ditto** (basic string matching, using DQL):
```swift
let result = await ditto.store.execute(
  query: "SELECT * FROM products WHERE product_name LIKE :searchTerm AND deleted = false",
  arguments: ["searchTerm": "%drill%"]
)
let products = result.items
```

### 6. Vector Similarity Search

**PostgreSQL** (pgvector):
```sql
SELECT product_id,
       1 - (description_embedding <=> $query_embedding) as similarity
FROM retail.product_description_embeddings
ORDER BY description_embedding <=> $query_embedding
LIMIT 10;
```

**MongoDB** (Atlas Vector Search):
```javascript
db.product_embeddings.aggregate([
  {
    $vectorSearch: {
      index: "vector_index",
      path: "description_embedding",
      queryVector: [0.123, ...],  // 1536 dimensions
      numCandidates: 100,
      limit: 10
    }
  },
  {
    $project: {
      product_id: 1,
      score: { $meta: "vectorSearchScore" }
    }
  }
])
```

**Ditto** (not supported):
```swift
// Vector search not available on device
// Must call backend API for semantic search
```

---

## Design Decision Rationale

### 1. Separate Collections for Order Items

**Decision**: Store order_items in separate collection, NOT embedded in orders

**Alternatives Considered**:
```javascript
// Option A: Embedded (rejected)
{
  "_id": "order_123",
  "items": [  // ❌ CRDT problem!
    { product_id: "prod_1", quantity: 2 },
    { product_id: "prod_2", quantity: 1 }
  ]
}

// Option B: Separate collection (chosen)
// orders collection
{ "_id": "order_123", ... }

// order_items collection
{ "_id": "uuid1", "order_id": "order_123", "product_id": "prod_1", ... }
{ "_id": "uuid2", "order_id": "order_123", "product_id": "prod_2", ... }
```

**Rationale**:
- ✅ CRDT-friendly: Each item is independent document
- ✅ No array conflicts: Concurrent updates don't interfere
- ✅ Variable item counts: 1-100+ items don't bloat order doc
- ✅ Flexible queries: Can query items independently
- ✅ Item-level updates: Returns, refunds, status changes

**Trade-off**: Requires 2 queries to get order + items (vs. 1 query with embedding)

### 2. UUID for Order Items

**Decision**: Use UUID v4 for order_items._id (not composite key, not sequence)

**Alternatives Considered**:
```javascript
// Option A: Composite {order_id, product_id} (rejected)
{ "_id": { "order_id": "order_123", "product_id": "prod_1" }, ... }
// Problem: Can't have same product twice at different prices

// Option B: Composite {order_id, item_seq} (rejected)
{ "_id": { "order_id": "order_123", "item_seq": 1 }, ... }
// Problem: Requires tracking last sequence number (pain offline)

// Option C: UUID (chosen)
{ "_id": "550e8400-e29b-41d4-a716-446655440000", ... }
```

**Rationale**:
- ✅ Simple: Just generate UUID, no state management
- ✅ Offline-friendly: Works without central sequence generator
- ✅ Flexible: Multiple same products at different prices
- ✅ 1:1 Ditto mapping: No duplicate fields needed

### 3. Separate Collection for Embeddings

**Decision**: Store embeddings in separate collection, NOT synced to Ditto

**Rationale**:
- ✅ Too large: 16-20KB per product × 400 = ~7MB
- ✅ Rarely needed on mobile: Vector search is server-side
- ✅ Keeps products small: 1-2KB vs 18-22KB
- ✅ Fetch on-demand: Mobile can request via API if needed

**Trade-off**: Requires $lookup to join products + embeddings for similarity search

### 4. Denormalized Fields in Orders

**Decision**: Copy customer_name, store_name into order documents

**Rationale**:
- ✅ Historical accuracy: Preserves names at time of order
- ✅ Offline display: Show orders without querying other collections
- ✅ Performance: One query instead of three
- ✅ Small overhead: ~100 bytes per order

**Trade-off**: Data duplication (~20MB for 200K orders)

### 5. Soft Deletes

**Decision**: Use deleted=true flag instead of removing documents

**Rationale**:
- ✅ Ditto requirement: MongoDB deletions "win" over Ditto changes
- ✅ Audit trail: Know what was deleted and when
- ✅ Undelete: Can reverse deletion if needed
- ✅ Sync safety: Avoid data loss from sync conflicts

**Trade-off**: Queries must always filter deleted==false (slight overhead)

---

## Trade-offs & Limitations

### Advantages of MongoDB + Ditto

**vs. PostgreSQL**:
| Feature | PostgreSQL | MongoDB + Ditto |
|---------|-----------|-----------------|
| Offline CRUD | ❌ No | ✅ Yes (full) |
| Peer-to-peer sync | ❌ No | ✅ Yes |
| Conflict resolution | ❌ Manual | ✅ Automatic (CRDTs) |
| Schema flexibility | ⚠️ Migrations | ✅ Flexible |
| Horizontal scaling | ⚠️ Limited | ✅ Excellent |
| Mobile-optimized | ❌ No | ✅ Yes |
| Vector search | ✅ pgvector | ✅ Atlas Vector Search |

### Limitations vs. PostgreSQL

| Feature | PostgreSQL | MongoDB + Ditto |
|---------|-----------|-----------------|
| FK constraints | ✅ Enforced | ❌ Application-level |
| Transactions | ✅ Full ACID | ⚠️ Limited (single DB) |
| Joins | ✅ SQL JOINs | ⚠️ $lookup (slower) |
| Complex queries | ✅ SQL power | ⚠️ Aggregation pipeline |
| Arrays for concurrent updates | ✅ Works | ❌ CRDT conflict |

### When to Use PostgreSQL

Use PostgreSQL when:
- ✅ Strong transactional guarantees required (banking)
- ✅ Complex joins across many tables
- ✅ Strict referential integrity needed
- ✅ Cloud-only, always online
- ✅ SQL expertise on team
- ✅ Advanced analytics (window functions, CTEs)

### When to Use MongoDB + Ditto

Use MongoDB + Ditto when:
- ✅ Offline-first mobile/edge applications
- ✅ Flexible, evolving schemas
- ✅ Horizontal scaling requirements
- ✅ Peer-to-peer sync needed
- ✅ Real-time collaborative applications
- ✅ Document-centric data (not highly relational)

---

## Migration Steps

### Phase 1: Preparation

1. **Review Schema Differences**
   - Read DATA_MODEL.md
   - Understand CRDT constraints
   - Identify problematic patterns (arrays)

2. **Set Up Infrastructure**
   - Create MongoDB Atlas cluster (M10+)
   - Enable Change Streams
   - Create Ditto Cloud app
   - Configure MongoDB Connector

3. **Create Environment Configuration**
   - Copy .env.sample to .env
   - Fill in MongoDB connection string
   - Add Ditto credentials
   - Add Azure OpenAI keys

### Phase 2: Data Transformation

1. **Transform Reference Data**
   ```bash
   python scripts/transform_reference_data.py
   # Converts seasonal multipliers: array → MAP
   ```

2. **Transform Product Data**
   ```bash
   python scripts/transform_product_data.py
   # Splits products from embeddings
   # Generates proper document structure
   ```

3. **Generate Full Dataset**
   ```bash
   python scripts/generate_zava_mongodb.py \
     --num-customers 50000 \
     --num-orders 200000
   # Generates all collections
   # Uses .env for credentials
   ```

### Phase 3: Validation

1. **Run Data Validation**
   ```bash
   python scripts/validate_data.py
   # Checks document counts
   # Validates foreign keys
   # Verifies indexes
   ```

2. **Run Tests**
   ```bash
   pytest tests/test_data_validation.py
   # Comprehensive validation tests
   # Must pass before proceeding
   ```

### Phase 4: Configure Ditto Connector

1. **Deploy Connector**
   - Upload config/ditto_connector_config.yaml
   - Start initial sync
   - Monitor progress in Ditto Portal

2. **Verify Sync**
   - Check collection counts in Ditto
   - Test CRUD operations
   - Verify conflict resolution

### Phase 5: Update Application Code

1. **Replace PostgreSQL Queries**
   ```python
   # OLD (PostgreSQL)
   cursor.execute("SELECT * FROM retail.orders WHERE order_id = %s", (order_id,))

   # NEW (MongoDB)
   order = db.orders.find_one({"order_id": order_id, "deleted": False})
   ```

2. **Update MCP Servers**
   - Modify customer_sales_mongodb.py
   - Modify sales_analysis_mongodb.py
   - Test with Claude Code

3. **Update Mobile Apps**
   ```swift
   // Ditto queries with DQL replace PostgreSQL
   let result = await ditto.store.execute(
     query: "SELECT * FROM orders WHERE _id = :orderId",
     arguments: ["orderId": orderId]
   )
   let order = result.items.first
   ```

### Phase 6: Testing

1. **Integration Tests**
   ```bash
   pytest tests/test_mongodb_integration.py
   ```

2. **Ditto Sync Tests**
   ```bash
   pytest tests/test_ditto_sync.py
   # Test offline scenarios
   # Test conflict resolution
   ```

3. **Performance Tests**
   ```bash
   pytest tests/test_performance.py
   # Benchmark queries
   # Compare to PostgreSQL baseline
   ```

### Phase 7: Deployment

1. **Deploy to Staging**
   - MongoDB Atlas (staging cluster)
   - Ditto Cloud (staging app)
   - Test with real devices

2. **Deploy to Production**
   - MongoDB Atlas (production cluster)
   - Ditto Cloud (production app)
   - Gradual rollout to users

---

## Comparison Tables

### Schema Comparison

| Aspect | PostgreSQL | MongoDB + Ditto |
|--------|-----------|-----------------|
| Tables/Collections | 10 tables | 9 collections |
| Relationships | Foreign keys | Referenced IDs |
| Constraints | DB-enforced | App-enforced |
| IDs | SERIAL (auto-increment) | String/UUID/Composite |
| Deletes | Hard delete | Soft delete (flag) |
| Seasonal data | Array | MAP (CRDT-friendly) |
| Embeddings | 2 tables | 1 collection |
| Inventory PK | Composite (store, product) | Composite _id object |
| Order items | SERIAL ID | UUID |

### Query Comparison

| Operation | PostgreSQL | MongoDB | Ditto (DQL) |
|-----------|-----------|---------|-------|
| Simple lookup | `SELECT * FROM orders WHERE id=1` | `find({ _id: 1 })` | `SELECT * FROM orders WHERE _id = 1` |
| Join | `JOIN customers ON ...` | `$lookup` aggregation | Subquery or 2 queries |
| Filter | `WHERE deleted=false` | `{ deleted: false }` | `WHERE deleted = false` |
| Sort | `ORDER BY date DESC` | `{ sort: { date: -1 } }` | `ORDER BY date DESC` |
| Limit | `LIMIT 10` | `{ limit: 10 }` | `LIMIT 10` |
| Aggregate | `GROUP BY, SUM, AVG` | Aggregation pipeline | Limited (app-level) |
| Text search | `to_tsvector` | Text index | `LIKE '%term%'` |
| Vector search | pgvector `<=>` | Atlas Vector Search | ❌ Not supported |

### Performance Comparison

| Metric | PostgreSQL | MongoDB + Ditto |
|--------|-----------|-----------------|
| Simple query | ~1ms | ~1ms (MongoDB), <1ms (Ditto local) |
| Join (3 tables) | ~5-10ms | ~10-20ms ($lookup) |
| Full-text search | ~10-50ms | ~10-50ms (text index) |
| Vector search | ~50-200ms | ~50-200ms (Atlas) |
| Write (single) | ~1-2ms | ~1-2ms (MongoDB), instant (Ditto) |
| Write (transaction) | ~5-10ms | ~5-10ms (MongoDB session) |
| Sync latency | N/A | ~100-500ms (device ↔ cloud) |
| Offline query | ❌ Not possible | ✅ <1ms (local) |

### Storage Comparison

| Metric | PostgreSQL | MongoDB |
|--------|-----------|---------|
| Total size | ~180 MB | ~243 MB |
| Embeddings | ~7 MB (vectors) | ~7 MB (arrays) |
| Orders | ~80 MB | ~100 MB (with denormalized fields) |
| Indexes | ~30 MB | ~40 MB |
| Overhead | Low (~10%) | Higher (~20-30%) due to BSON |

---

## Summary

### Key Changes
1. ✅ Separate collections for order items (CRDT-friendly)
2. ✅ UUIDs for offline ID generation
3. ✅ MAPs instead of arrays for concurrent updates
4. ✅ Denormalized fields for offline display
5. ✅ Soft deletes for sync safety
6. ✅ Composite IDs for natural keys
7. ✅ Separate embeddings collection (not synced)

### Key Benefits
1. ✅ Full offline CRUD operations
2. ✅ Automatic conflict resolution
3. ✅ Peer-to-peer sync capability
4. ✅ Flexible schema evolution
5. ✅ Horizontal scalability

### Key Trade-offs
1. ⚠️ Application-level FK validation
2. ⚠️ Limited transactions (single DB)
3. ⚠️ Two-query pattern for joins
4. ⚠️ Data duplication (~30% overhead)
5. ⚠️ Must filter soft deletes in queries

**Migration is recommended for**: Mobile-first, offline-capable retail applications with real-time sync requirements.

---

**Document Version**: 1.0
**Last Updated**: 2024-12-05
**Related**: [DATA_MODEL.md](DATA_MODEL.md) | [ARCHITECTURE.md](ARCHITECTURE.md)
