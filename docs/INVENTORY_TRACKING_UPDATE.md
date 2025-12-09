# Inventory Tracking Update - Design Changes

**Date**: 2024-12-05
**Status**: Phase 1 Documentation Updates Complete

---

## Changes Overview

Based on user requirements, the data model has been updated to focus on inventory tracking with location data and UUID-based IDs for the inventory collection.

---

## Key Changes

### 1. Inventory Collection: Composite ID → UUID

**Before** (Composite ID):
```json
{
  "_id": {
    "store_id": "store_seattle",
    "product_id": "prod_drill_001"
  },
  "store_id": "store_seattle",    // Duplicated
  "product_id": "prod_drill_001",  // Duplicated
  "stock_level": 50
}
```

**After** (UUID):
```json
{
  "_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID
  "store_id": "store_seattle",
  "product_id": "prod_drill_001",
  "location": {
    "aisle": "3",
    "shelf": "B",
    "bin": "12"
  },
  "stock_level": 50,
  "last_updated": "2024-12-05T14:22:00Z",
  "last_counted": "2024-12-01T09:00:00Z",
  "notes": "High demand item"
}
```

**Rationale**:
- **Consistency**: Same pattern as order_items (UUID-based, simple)
- **Offline-friendly**: UUIDs work offline without central ID generator
- **Simpler connector**: 1:1 ID mapping (match_ids) vs. multiple_fields
- **Flexibility**: Allows multiple locations per product per store if needed

### 2. Added Location Tracking Fields

**New Fields**:
- `location` (object/MAP): Physical location in store
  - `location.aisle`: Aisle number/identifier (e.g., "3", "A1")
  - `location.shelf`: Shelf identifier (e.g., "B", "Top", "2")
  - `location.bin`: Optional bin/section number
- `last_counted`: Last physical count date
- `notes`: Worker notes (seasonal, high demand, etc.)

**Use Cases**:
- **Worker app**: Find products quickly via aisle/shelf lookup
- **Inventory audits**: Compare expected vs. actual counts
- **Restocking**: Know exact location for replenishment
- **Training**: New employees can find items easily

### 3. Demo Focus: Worker App & Sales Rep App

**Worker App** (Store Employee):
- Find product location in store
- Check real-time inventory levels
- Receive low stock alerts
- Move inventory between stores
- Order items from warehouse
- Perform physical counts
- Track inventory after orders (dynamic updates)

**Sales Rep App** (Customer-focused):
- Browse products offline
- Check availability across stores
- View customer order history
- Create orders with inventory validation
- Prevent overselling

### 4. Ditto Connector ID Mapping Change

**Before**:
```yaml
- name: inventory
  id_mapping:
    mode: multiple_fields
    fields: [store_id, product_id]
```

**After**:
```yaml
- name: inventory
  id_mapping:
    mode: match_ids  # UUID same in both systems
```

### 5. Updated Query Patterns (Using DQL)

**Find product location** (Worker App):
```swift
let result = await ditto.store.execute(
  query: "SELECT * FROM inventory WHERE store_id = :storeId AND product_id = :productId",
  arguments: [
    "storeId": "store_seattle",
    "productId": "prod_drill_001"
  ]
)
let item = result.items.first
// Returns: { location: { aisle: "3", shelf: "B" }, stock_level: 50 }
```

**Get low stock items** (Reorder Alerts):
```swift
let result = await ditto.store.execute(
  query: "SELECT * FROM inventory WHERE store_id = :storeId AND stock_level <= reorder_threshold",
  arguments: ["storeId": "store_seattle"]
)
let lowStock = result.items
```

**Update inventory after order** (Dynamic tracking):
```swift
await ditto.store.execute(
  query: """
    UPDATE inventory
    SET stock_level = stock_level - :quantity,
        last_updated = :timestamp
    WHERE _id = :inventoryId
  """,
  arguments: [
    "quantity": quantity,
    "timestamp": Date().isoformat(),
    "inventoryId": inventoryId
  ]
)
```

---

## Files Updated

### Documentation (Phase 1)

1. **`DATA_MODEL.md`**:
   - ✅ Updated inventory collection schema (UUID + location fields)
   - ✅ Updated relationship diagrams
   - ✅ Updated Ditto connector ID mappings
   - ✅ Added inventory-focused query patterns
   - ✅ Updated subscription patterns for worker/sales rep apps

2. **`PLAN.md`**:
   - ✅ Updated Ditto connector config (inventory: match_ids)
   - ✅ Updated demo scenarios (worker app, sales rep app, inventory focus)

3. **`INVENTORY_TRACKING_UPDATE.md`** (this file):
   - ✅ Comprehensive change log

### Still To Update

4. **`ARCHITECTURE.md`**:
   - ⏳ Update deployment architecture with worker/sales rep apps
   - ⏳ Update data flow diagrams for inventory updates
   - ⏳ Add demo scenarios section

5. **`MIGRATION_GUIDE.md`**:
   - ⏳ Update inventory schema migration
   - ⏳ Remove composite ID examples
   - ⏳ Add UUID + location tracking rationale

6. **`Claude.md`**:
   - ⏳ Update final data model design section
   - ⏳ Update key design decisions

---

## Implementation Impact

### Data Generation (Phase 3)

**Changes Required**:
- Generate UUIDs for inventory._id (not composite objects)
- Generate realistic location data (aisle, shelf, bin)
- Add last_counted dates
- Add worker notes for some items

**Example Generation Code**:
```python
import uuid

inventory_item = {
    "_id": str(uuid.uuid4()),
    "store_id": store_id,
    "product_id": product_id,
    "location": {
        "aisle": random.choice(["1", "2", "3", "4", "5", "A1", "B2"]),
        "shelf": random.choice(["A", "B", "C", "Top", "Middle", "Bottom"]),
        "bin": random.choice([None, "1", "2", "12", "24"])
    },
    "stock_level": random.randint(0, 100),
    "reorder_threshold": random.randint(5, 20),
    "last_updated": datetime.now().isoformat(),
    "last_counted": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
    "notes": random.choice([None, "High demand", "Seasonal", "Check weekly"]),
    "deleted": False
}
```

### Ditto Connector (Phase 4)

**Config Update**:
```yaml
collections:
  - name: inventory
    id_mapping:
      mode: match_ids  # Changed from multiple_fields
    sync_enabled: true
```

### Tests (Phase 7)

**New Validation Tests**:
- ✅ Test inventory._id is UUID format
- ✅ Test location is MAP (not array)
- ✅ Test location.aisle and location.shelf exist
- ✅ Test query by store_id returns correct items
- ✅ Test query by product_id returns correct items
- ✅ Test low stock query works
- ✅ Test inventory update decrements stock_level

---

## Benefits

### For Workers
- **Faster product location**: "It's in Aisle 3, Shelf B"
- **Real-time stock visibility**: Know immediately when low
- **Offline capability**: Use app anywhere in store/warehouse
- **Efficient restocking**: Exact location for replenishment

### For Sales Reps
- **Avoid overselling**: Real-time inventory checks
- **Multi-store visibility**: See stock across all locations
- **Customer confidence**: Accurate availability information
- **Offline orders**: Create orders without connectivity

### For Developers
- **Simpler model**: UUID vs. composite key (less code)
- **CRDT-friendly**: MAPs for location, independent updates
- **Flexible queries**: Filter by store, product, or location
- **Future-proof**: Can add multiple locations per product if needed

---

## Open Questions / Future Enhancements

1. **Multiple locations per product?**
   - Current: One inventory record per product per store
   - Future: Support multiple physical locations (warehouse + showroom)?
   - Solution: UUID model already supports this (just add more documents)

2. **Inventory transfers between stores?**
   - Need workflow: Decrement from source, increment at destination
   - Track transfer status: pending, in-transit, received
   - Possible: Add `inventory_transfers` collection

3. **Warehouse vs. Store inventory?**
   - Add `location_type` field: "warehouse", "showroom", "backroom"
   - Different reorder thresholds by location type

4. **Barcode scanning?**
   - Add `barcode` field to products
   - Worker app scans to find location/update counts

---

## Next Steps

1. ✅ Complete Phase 1 documentation updates
2. ⏭️ Update remaining docs (ARCHITECTURE.md, MIGRATION_GUIDE.md, Claude.md)
3. ⏭️ Phase 2: MongoDB setup (indexes for location queries)
4. ⏭️ Phase 3: Data generation (UUID + location data)
5. ⏭️ Phase 4: Ditto connector (UUID mapping)
6. ⏭️ Phase 7: Validation tests (location fields, UUID format)

---

**Status**: Phase 1 in progress - documentation updates underway.
