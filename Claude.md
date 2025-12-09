# Zava DIY Retail - MongoDB + Ditto Conversion Summary

This document summarizes the research, analysis, and design decisions made during the planning phase of converting the Zava DIY Retail demo from PostgreSQL to MongoDB + Ditto.

---

## Table of Contents
1. [Original Dataset Analysis](#original-dataset-analysis)
2. [MongoDB Data Modeling Research](#mongodb-data-modeling-research)
3. [Ditto CRDT Constraints](#ditto-crdt-constraints)
4. [MongoDB Connector Requirements](#mongodb-connector-requirements)
5. [Final Data Model Design](#final-data-model-design)
6. [Key Design Decisions](#key-design-decisions)
7. [Trade-offs and Considerations](#trade-offs-and-considerations)

---

## Original Dataset Analysis

### Source Repository
Microsoft demo retail app originally designed for PostgreSQL and SQL Server, showcasing:
- Row-Level Security (RLS) for multi-tenant access
- AI embeddings (image + text) for semantic search
- Realistic seasonal sales patterns
- 6 years of historical data (2020-2026)

### Data Model Structure

**10 Tables (Relational Model)**:
1. **stores** (8 records) - Physical locations + 1 online store in Washington State
2. **customers** (50,000) - Demographics, contact info, primary store association
3. **categories** (9) - Product categories (Hand Tools, Power Tools, Paint, etc.)
4. **product_types** (~30) - Sub-categories within main categories
5. **products** (400) - Complete catalog with SKU, pricing, descriptions
6. **product_image_embeddings** - 512-dimensional vectors (OpenAI CLIP)
7. **product_description_embeddings** - 1536-dimensional vectors (Azure OpenAI)
8. **inventory** (3,000) - Store-specific stock levels (composite key: store_id + product_id)
9. **orders** (200,000) - Order headers spanning 2020-2026
10. **order_items** (200,000-500,000) - Line items with pricing, discounts

### Key Features
- **Seasonal Intelligence**: Paint peaks in spring (2.2x), garden in summer, lumber in June-July
- **Year-over-Year Growth**: 2020 baseline (1.0) → 2026 (1.531x growth)
- **Store-Specific Patterns**: Seattle & Online highest volume (3.0x multiplier)
- **Consistent Margins**: All products maintain 33% gross margin
- **Multi-Tenant Security**: UUID-based RLS policies per store

### Data Generation Method
- Python scripts using `asyncpg` (PostgreSQL) or `pyodbc` (SQL Server)
- Faker library for realistic customer data
- JSON source files with pre-computed embeddings
- Sophisticated seasonal and growth algorithms
- Batch insert operations with indexing strategies

---

## MongoDB Data Modeling Research

### Embedding vs. Referencing (MongoDB Best Practices)

**When to Embed**:
- ✅ Data accessed together frequently
- ✅ Bounded, small data (won't grow unboundedly)
- ✅ Atomic updates needed
- ✅ Read-heavy workloads

**When to Reference**:
- ✅ Data changes frequently and independently
- ✅ Unbounded growth potential (e.g., orders per customer)
- ✅ Large data that exceeds 16MB document limit
- ✅ Related entity queried independently

### Document Size Constraints
- **Hard Limit**: 16MB per document (BSON format)
- **Performance Degradation**: Documents >2MB cause significant query slowdowns
- **Unbounded Arrays**: Official MongoDB anti-pattern

### MongoDB Patterns for Relational Data

**1. Reference Pattern (Normalized)**
```javascript
// Separate collections with IDs
{ _id: "order_123", customer_id: "cust_456", ... }
{ _id: "item_001", order_id: "order_123", ... }
```
- Most similar to SQL
- Requires application-level joins or `$lookup`
- Best for unbounded relationships

**2. Extended Reference Pattern (Hybrid)**
```javascript
// Embed frequently accessed fields, reference for full data
{
  _id: "order_123",
  customer_id: "cust_456",
  customer_name: "John Smith",  // denormalized
  items: [
    { product_id: "prod_999", name: "Drill", price: 149.99 }
  ]
}
```
- **MongoDB's recommended pattern** to reduce `$lookup` operations
- Trade-off: Data duplication vs. query performance
- Good for moderate array sizes (1-50 items)

**3. Subset Pattern**
```javascript
// Embed most recent N items, reference the rest
{
  _id: "order_123",
  items_preview: [ /* first 10 items */ ],
  has_more_items: true
}
```
- Handles outliers gracefully
- Most docs small, overflow handled separately

### MongoDB Official Guidance on Orders/Items

> "If you think information can grow tremendously over the period, avoid embedding. For example, if you are thinking to keep user and his orders in same collection, it's not a good idea as order details can be large and it can grow over the period."

**Conclusion**: MongoDB explicitly recommends **NOT** embedding order items in orders.

---

## Ditto CRDT Constraints

### Critical Array Limitation

**From Ditto Documentation**:
> "Avoid using arrays in Ditto. Due to potential merge conflicts when offline peers reconnect to the mesh and attempt to sync their updates, especially when multiple peers make concurrent updates to the same item within the array."

**Why?**
- Arrays are **REGISTER types** (last-write-wins, atomic)
- Concurrent modifications to array indices create conflicts
- During sync, one peer's array "wins," other changes are lost
- No automatic merging like MAPs

**Example Conflict Scenario**:
```
Peer A (offline): items[0].quantity = 5
Peer B (offline): items[0].quantity = 3
On reconnect: Only one value survives (CRDT conflict)
```

### Recommended Alternative: MAPs

**From Ditto Documentation**:
> "Using a JSON object within a MAP allows you to automatically merge the contents of the MAP when offline peers reconnect to the mesh."

**MAPs Use Add-Wins Semantics**:
- Each key-value pair modifiable independently
- Conflicting changes retained and merged
- Example: `{ jan: 0.8, feb: 0.9, ... }` instead of `[0.8, 0.9, ...]`

### When Arrays Are Acceptable in Ditto

Arrays are OK for:
- ✅ **Write-once, immutable data** (completed orders, historical records)
- ✅ **Single-writer scenarios** (one peer owns the document)
- ✅ **Bounded, atomic data** (coordinates: `[lat, lng]`)

Arrays are **NOT OK** for:
- ❌ **Concurrent updates** from multiple peers
- ❌ **Growing collections** (shopping cart, line items)
- ❌ **Independent element updates** (inventory per store)

---

## MongoDB Connector Requirements

### Bidirectional Synchronization
- Listens to MongoDB Change Streams
- Uses CRDTs for conflict resolution
- Syncs deltas (not full documents) for efficiency
- CRDT-based conflict resolution (no custom services needed)

### Data Type Mapping

**Native BSON Mapping (Recommended)**:
| MongoDB Type | Ditto Type |
|--------------|------------|
| Double | number |
| String | string |
| Object | MAP (object) |
| Array | REGISTER (array) |
| ObjectId | string |
| Boolean | boolean |
| Date | string (ISO8601) |
| Integer | integer |

**EJSON Mode** (verbose, not recommended):
- `ISODate` → `{ "$date": { "$numberLong": "..." } }`
- More complex application code needed

### ID Mapping Requirements

**Critical Constraints**:
- ID fields must be **immutable and always present**
- **Only top-level fields** (no nested paths like `user.id`)
- **Cannot be null or arrays**
- Objects allowed only in multi-field mappings

**Three Mapping Modes**:

1. **1:1 Mode (Match IDs)**
   - MongoDB `_id` = Ditto `_id` (identical)
   - Simplest, but requires compatible ID format

2. **Single Field Mode**
   - Map one MongoDB field → Ditto `_id`
   - Example: `customer_id` → Ditto `_id`

3. **Multiple Field Mode (Composite)**
   - Map multiple fields → Ditto composite `_id` object
   - Example: `[store_id, product_id]` → `{ store_id: "...", product_id: "..." }`

### Best Practice: Duplicate ID Fields

**From Ditto Documentation**:
> "Duplicate ID fields in document bodies alongside the `_id` to facilitate application patterns."

**Example**:
```json
{
  "_id": { "store_id": "store_789", "product_id": "prod_999" },
  "store_id": "store_789",  // Duplicated for Ditto queries
  "product_id": "prod_999",  // Duplicated for Ditto queries
  "stock_level": 50
}
```

**Why?**
- Enables Ditto permission scoping: `WHERE store_id = '$currentStoreId'`
- Allows MongoDB queries without complex `_id` navigation
- Required for connector to map fields to Ditto `_id`

### Collection Requirements
- **Change Streams** must be enabled with `changeStreamPreAndPostImages`
- Collections **must exist in MongoDB** before connector setup
- Metadata stored in `__ditto_connector_sessions`
- Failed syncs stored in `__ditto_unsynced_documents`

### Soft Delete Pattern

**From Ditto Documentation**:
> "You should generally treat deletions as a final state and implement soft-deletes via MongoDB if reversibility is needed."

**Why?**
- MongoDB deletions "win" over Ditto changes
- Even if Ditto recreates a document, MongoDB deletion prevails
- Soft delete: Add `deleted: true` flag instead of removing document

---

## Final Data Model Design

### Design Principles

1. ✅ **Avoid arrays for concurrent writes** (inventory, active carts)
2. ✅ **Arrays OK for immutable data** (completed order items)
3. ✅ **Use composite IDs** where natural (store+product inventory)
4. ✅ **Duplicate ID fields** in document body (Ditto requirement)
5. ✅ **Separate embeddings** from main collections (too large for mobile)
6. ✅ **Soft deletes** instead of hard deletes (connector requirement)
7. ✅ **Use UUIDs** for simplicity (order_items, avoid sequence management)

### Collection Schemas

#### 1. stores (8 documents)
```json
{
  "_id": "store_seattle",
  "store_id": "store_seattle",
  "store_name": "Zava Retail Seattle",
  "rls_user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "is_online": false,
  "location": {  // MAP - safe for CRDTs
    "address": "123 Main St",
    "city": "Seattle",
    "state": "WA",
    "zip": "98101"
  },
  "deleted": false
}
```
**Connector**: Single field → `store_id`

#### 2. customers (50,000 documents)
```json
{
  "_id": ObjectId("..."),
  "customer_id": "cust_456",
  "first_name": "John",
  "last_name": "Smith",
  "email": "john@email.com",
  "phone": "(206) 555-0123",
  "primary_store_id": "store_seattle",
  "created_at": "2024-03-15T10:30:00Z",
  "deleted": false
}
```
**Connector**: Single field → `customer_id`

#### 3. categories (9 documents)
```json
{
  "_id": "cat_power_tools",
  "category_id": "cat_power_tools",
  "category_name": "Power Tools",
  "seasonal_multipliers": {  // MAP not array!
    "jan": 0.8,
    "feb": 0.9,
    "mar": 1.2,
    // ... 12 months
  },
  "deleted": false
}
```
**Connector**: Match IDs (1:1)
**Why MAP**: Each month independently updatable, no array conflicts

#### 4. products (400 documents)
```json
{
  "_id": "prod_pwr_drill_001",
  "product_id": "prod_pwr_drill_001",
  "sku": "PWR-DRILL-001",
  "product_name": "20V Cordless Drill",
  "category_id": "cat_power_tools",
  "cost": 100.00,
  "base_price": 149.99,
  "gross_margin_percent": 33.00,
  "product_description": "Professional grade...",
  "specifications": {  // MAP
    "voltage": "20V",
    "battery_type": "Lithium-Ion",
    "weight_lbs": 3.5
  },
  "deleted": false
}
```
**Connector**: Single field → `product_id`
**Note**: Embeddings stored separately (NOT synced to Ditto)

#### 5. product_embeddings (400 documents, MongoDB only)
```json
{
  "_id": "prod_pwr_drill_001",
  "product_id": "prod_pwr_drill_001",
  "image_embedding": [0.123, ...],  // 512 dimensions
  "description_embedding": [0.234, ...],  // 1536 dimensions
  "image_url": "/images/drill.jpg",
  "created_at": "2024-01-15T10:30:00Z"
}
```
**Connector**: ❌ **NOT SYNCED** (too large for mobile ~16-20KB per doc)
**Usage**: Server-side vector search only, fetch on-demand via API

#### 6. inventory (3,000 documents)
```json
{
  "_id": {
    "store_id": "store_seattle",
    "product_id": "prod_pwr_drill_001"
  },
  "store_id": "store_seattle",  // Duplicated
  "product_id": "prod_pwr_drill_001",  // Duplicated
  "stock_level": 50,
  "last_updated": "2024-12-05T14:22:00Z",
  "deleted": false
}
```
**Connector**: Multiple fields → `[store_id, product_id]`
**Why composite ID**: Natural key, each store-product pair isolated (no conflicts)

#### 7. orders (200,000 documents)
```json
{
  "_id": "order_20251205_001",
  "order_id": "order_20251205_001",
  "customer_id": "cust_456",
  "store_id": "store_seattle",
  "order_date": "2025-01-15T10:30:00Z",

  // Denormalized read-only snapshots
  "customer_name": "John Smith",
  "store_name": "Zava Retail Seattle",

  // Summary fields
  "item_count": 2,
  "subtotal": 299.98,
  "total": 314.23,

  "status": "completed",
  "deleted": false
}
```
**Connector**: Single field → `order_id`
**Note**: NO embedded items array (separate collection)

#### 8. order_items (200,000-500,000 documents)
```json
{
  "_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID
  "order_id": "order_20251205_001",
  "product_id": "prod_pwr_drill_001",

  // Denormalized product snapshot
  "sku": "PWR-DRILL-001",
  "product_name": "20V Cordless Drill",

  // Line item details
  "quantity": 2,
  "unit_price": 149.99,
  "discount_percent": 10,
  "line_total": 284.98,

  "deleted": false
}
```
**Connector**: Match IDs (1:1) - UUID
**Why separate**: No array conflicts, variable item counts, flexible queries

---

## Key Design Decisions

### 1. UUID for Order Items (Not Composite ID)

**Decision**: Use simple UUID `_id` instead of composite `{order_id, product_id}` or `{order_id, item_seq}`

**Rationale**:
- ✅ **Simplest implementation** - just generate UUID, no sequence management
- ✅ **Maximum flexibility** - can have multiple line items for same product (different prices)
- ✅ **No duplicate field overhead** - connector uses 1:1 mapping
- ✅ **Realistic for demos** - most e-commerce systems use synthetic IDs

**Rejected Alternatives**:
- ❌ `{order_id, item_seq}` - Requires tracking last sequence number (pain to manage)
- ❌ `{order_id, product_id}` - Prevents multiple items of same product at different prices

### 2. Separate Collection for Order Items (Not Embedded Array)

**Decision**: Store order items in separate collection, NOT embedded in orders

**Rationale**:
- ✅ **Avoids CRDT array conflicts** - Each item is independent document
- ✅ **Variable item counts** - 1-100+ items don't bloat order document
- ✅ **Keeps order docs small** - <2KB for fast sync
- ✅ **Flexible queries** - Can query items independently
- ✅ **Enables item-level updates** - Returns, refunds, status changes

**Could we use arrays?**
- Technically YES (orders are write-once after completion)
- But NO for flexibility and consistency with other patterns

### 3. Separate Collection for Embeddings (Not Synced to Ditto)

**Decision**: Store embeddings in separate `product_embeddings` collection, exclude from Ditto sync

**Rationale**:
- ✅ **Too large for mobile** - 16-20KB per product × 400 = 6-8MB just for embeddings
- ✅ **Rarely queried on mobile** - Vector search typically server-side only
- ✅ **Keeps product docs small** - 1-2KB vs 18-22KB
- ✅ **Fetch on-demand** - Mobile can request via API if needed
- ✅ **Faster sync** - Reduces data transfer by 90%

**Query Pattern**:
- MongoDB: Join products ↔ embeddings for similarity search
- Ditto: Query products only, embeddings fetched via REST API if needed

### 4. MAPs for Seasonal Multipliers (Not Arrays)

**Decision**: Store seasonal data as MAP `{jan: 0.8, feb: 0.9, ...}` not array `[0.8, 0.9, ...]`

**Rationale**:
- ✅ **CRDT-friendly** - Each month independently updatable
- ✅ **No merge conflicts** - Multiple peers can update different months
- ✅ **Self-documenting** - `seasonal_multipliers.jun` vs `seasonal_multipliers[5]`
- ✅ **Follows Ditto best practices** - Avoid arrays for concurrent updates

### 5. Duplicate ID Fields (Required by Ditto Connector)

**Decision**: Duplicate ID fields in document body alongside `_id`

**Example**:
```json
{
  "_id": { "store_id": "store_789", "product_id": "prod_999" },
  "store_id": "store_789",  // Duplicated
  "product_id": "prod_999"  // Duplicated
}
```

**Rationale**:
- ✅ **Ditto connector requirement** - Needs top-level fields for ID mapping
- ✅ **Enables Ditto queries** - `WHERE store_id = 'X'` (can't query `_id.store_id` easily)
- ✅ **Simplifies MongoDB queries** - No need to navigate into `_id` object
- ✅ **Permission scoping** - Ditto permissions use field values

### 6. Soft Deletes (Not Hard Deletes)

**Decision**: Add `deleted: false` flag to all documents, never actually delete

**Rationale**:
- ✅ **Connector requirement** - MongoDB deletions "win" over Ditto changes
- ✅ **Data recovery** - Can undelete if needed
- ✅ **Audit trail** - Keep history of what was deleted and when
- ✅ **Sync safety** - Avoid data loss from accidental deletes

**Implementation**:
```json
{ "deleted": false }  // Active
{ "deleted": true, "deleted_at": "2024-12-05T10:00:00Z" }  // Soft deleted
```

**Queries**: Always filter `deleted == false` unless explicitly querying deleted items

### 7. Denormalized Fields in Orders

**Decision**: Copy customer/store names into order documents

**Example**:
```json
{
  "order_id": "order_123",
  "customer_id": "cust_456",
  "customer_name": "John Smith",  // Denormalized
  "customer_email": "john@email.com",  // Denormalized
  "store_id": "store_789",
  "store_name": "Zava Retail Seattle"  // Denormalized
}
```

**Rationale**:
- ✅ **Historical accuracy** - Preserves customer/store info at time of order
- ✅ **Faster queries** - No need to join customers/stores for display
- ✅ **Offline-first friendly** - Can display order without querying other collections
- ✅ **Small overhead** - ~100 bytes per order for significant UX improvement

**Trade-off**: Data duplication, but this is **intentional** (historical snapshot)

---

## Trade-offs and Considerations

### Advantages of MongoDB + Ditto Approach

**vs. PostgreSQL**:
- ✅ **Offline-first** - Full CRUD operations work offline, sync when online
- ✅ **Edge computing** - Data lives on devices, not just cloud
- ✅ **Flexible schema** - Add fields without migrations
- ✅ **Horizontal scaling** - MongoDB sharding, Ditto mesh network
- ✅ **Mobile-optimized** - Small documents, efficient sync protocols
- ✅ **CRDT conflict resolution** - Automatic, no manual intervention
- ✅ **Vector search built-in** - MongoDB Atlas Vector Search

**vs. Traditional Sync Solutions**:
- ✅ **No custom backend** - CRDTs eliminate conflict resolution services
- ✅ **Peer-to-peer capable** - Devices can sync directly (no cloud required)
- ✅ **Delta sync** - Only changes transmitted, not full documents

### Disadvantages and Limitations

**vs. PostgreSQL**:
- ❌ **No transactions across collections** - MongoDB transactions limited vs. SQL
- ❌ **No foreign key constraints** - Application must enforce referential integrity
- ❌ **More storage** - Denormalized data duplicates information
- ❌ **Two-query pattern** - Orders+items requires 2 queries (vs. 1 SQL JOIN)
- ❌ **Array limitations** - Can't use arrays for concurrent updates (CRDT constraint)

**MongoDB Connector Specific**:
- ⚠️ **Only top-level ID mapping** - Can't map nested fields to Ditto `_id`
- ⚠️ **Change Streams required** - Older MongoDB versions not supported
- ⚠️ **Initial sync manual** - Existing data doesn't auto-sync unless modified
- ⚠️ **No $lookup in Ditto** - Must do joins at application level

### When to Use PostgreSQL vs. MongoDB+Ditto

**Use PostgreSQL when**:
- ✅ Strong transactional requirements (banking, accounting)
- ✅ Complex joins across many tables
- ✅ Strict referential integrity needed
- ✅ Cloud-only, always online
- ✅ SQL expertise on team

**Use MongoDB + Ditto when**:
- ✅ Offline-first mobile/edge applications
- ✅ Flexible, evolving schemas
- ✅ Horizontal scaling requirements
- ✅ Peer-to-peer sync needed
- ✅ Bounded document relationships
- ✅ Real-time collaborative applications

### Performance Characteristics

**Document Sizes**:
| Collection | Avg Size | Max Size | Count | Total |
|------------|----------|----------|-------|-------|
| stores | 500 B | 1 KB | 8 | 4 KB |
| customers | 300 B | 500 B | 50K | 15 MB |
| categories | 400 B | 500 B | 9 | 4 KB |
| products | 1-2 KB | 5 KB | 400 | 600 KB |
| embeddings | 16-20 KB | 25 KB | 400 | 7 MB |
| inventory | 200 B | 300 B | 3K | 600 KB |
| orders | 500 B | 1 KB | 200K | 100 MB |
| order_items | 300 B | 500 B | 400K | 120 MB |

**Total Storage**:
- **MongoDB** (all data): ~243 MB
- **Ditto** (without embeddings): ~236 MB
- **Mobile sync** (filtered subscriptions): ~10-50 MB typical

**Query Performance** (estimated):
- Simple lookups (by `_id`): <1ms
- Indexed queries (customer_id, order_id): <5ms
- Aggregations (order + items): 10-50ms
- Vector similarity search: 50-200ms (depends on index)
- Full collection scans: Avoid (use indexes)

### Sync Performance

**Initial Sync** (Ditto connector):
- Rate limited to prevent overload
- Background process, non-blocking
- Estimate: 200K orders @ 500B = 100MB → ~5-10 minutes

**Incremental Sync** (real-time):
- Only deltas transmitted
- Typical order: ~1KB → <100ms to sync
- CRDT merge: <10ms per document

**Mobile Device Sync**:
- Subscription-based (only relevant data)
- Example: Store manager → 1 store's data (~1-2 MB)
- Example: Sales rep → 100 customers (~1 MB)
- Background sync with exponential backoff

---

## Query Pattern Examples

### MongoDB (Cloud/Backend)

**Get order with items**:
```javascript
db.orders.aggregate([
  { $match: { order_id: "order_123" } },
  { $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
  }}
])
```

**Vector similarity search**:
```javascript
db.product_embeddings.aggregate([
  { $vectorSearch: {
      index: "vector_index",
      path: "description_embedding",
      queryVector: [...],
      limit: 10
  }},
  { $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "product_id",
      as: "product"
  }}
])
```

### Ditto (Mobile/Edge)

**Get order with items** (2 queries):
```swift
// Query 1
let order = try await ditto
  .store.collection("orders")
  .findById("order_123").exec()

// Query 2
let items = try await ditto
  .store.collection("order_items")
  .find("order_id == 'order_123'").exec()
```

**Subscription for offline sync**:
```swift
// Sync only this store's data
ditto.sync.subscribe(
  collection: "inventory",
  query: "_id.store_id == 'store_seattle'"
)
```

---

## Conclusion

This conversion transforms a traditional cloud-based relational database into a modern offline-first distributed system while maintaining all core functionality. The design carefully balances:

- **Simplicity** (UUIDs, normalized collections)
- **Performance** (small documents, efficient indexes)
- **CRDT compatibility** (MAPs not arrays, separate collections)
- **Mobile optimization** (exclude embeddings, subscription filters)
- **Realism** (denormalized historical data, soft deletes)

The resulting architecture supports both server-side analytics (MongoDB) and edge computing (Ditto) with seamless bidirectional synchronization.

---

## References

- **Original Repo**: microsoft/ai-tour-26-zava-diy-dataset
- **MongoDB Documentation**: https://docs.mongodb.com/manual/data-modeling/
- **Ditto Documentation**: https://docs.ditto.live/
- **Ditto MongoDB Connector**: https://docs.ditto.live/cloud/mongodb-connector
- **MongoDB Vector Search**: https://www.mongodb.com/products/platform/atlas-vector-search
- **CRDT Research**: https://crdt.tech/

---

**Document Status**: Planning Complete - Ready for Implementation
**Last Updated**: 2024-12-05
**Next Step**: Review PLAN.md and begin Phase 1 (Documentation)
