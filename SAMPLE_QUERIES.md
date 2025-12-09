# Sample Queries - MongoDB + Ditto

This document provides sample queries for the Zava Retail demo application showing both MongoDB (server-side) and Ditto (mobile/edge) query patterns.

---

## Table of Contents

1. [MongoDB Queries](#mongodb-queries)
2. [Ditto Queries](#ditto-queries)
3. [Common Use Cases](#common-use-cases)
4. [Performance Optimization](#performance-optimization)

---

## MongoDB Queries

### Basic Lookups

#### Get Store by ID
```javascript
db.stores.findOne({ store_id: "store_seattle" })
```

#### Get Product by SKU
```javascript
db.products.findOne({ sku: "PWR-DRILL-001" })
```

#### Get Customer by Email
```javascript
db.customers.findOne({ email: "john.smith@example.com" })
```

### Inventory Queries

#### Get Inventory for a Store
```javascript
db.inventory.find({
  store_id: "store_seattle",
  deleted: false
})
```

#### Low Stock Alert
```javascript
db.inventory.aggregate([
  {
    $match: {
      $expr: { $lt: ["$stock_level", "$reorder_threshold"] },
      deleted: false
    }
  },
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
      from: "stores",
      localField: "store_id",
      foreignField: "store_id",
      as: "store"
    }
  },
  { $unwind: "$store" },
  {
    $project: {
      store_name: "$store.store_name",
      product_name: "$product.product_name",
      sku: "$product.sku",
      stock_level: 1,
      reorder_threshold: 1,
      location: 1
    }
  }
])
```

#### Find Product by Aisle
```javascript
db.inventory.find({
  "location.aisle": "A1",
  deleted: false
})
```

### Order Queries

#### Get Order with Items
```javascript
db.orders.aggregate([
  { $match: { order_id: "order_20251205_001" } },
  {
    $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
    }
  },
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "customer_id",
      as: "customer"
    }
  },
  { $unwind: { path: "$customer", preserveNullAndEmptyArrays: true } }
])
```

#### Customer Order History
```javascript
db.orders.aggregate([
  {
    $match: {
      customer_id: "cust_456",
      deleted: false
    }
  },
  { $sort: { order_date: -1 } },
  { $limit: 10 },
  {
    $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
    }
  }
])
```

#### Top Products by Revenue (Last 30 Days)
```javascript
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

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
  {
    $match: {
      "order.order_date": { $gte: thirtyDaysAgo.toISOString() },
      "order.deleted": false,
      deleted: false
    }
  },
  {
    $group: {
      _id: "$product_id",
      product_name: { $first: "$product_name" },
      sku: { $first: "$sku" },
      total_quantity: { $sum: "$quantity" },
      total_revenue: { $sum: "$line_total" }
    }
  },
  { $sort: { total_revenue: -1 } },
  { $limit: 10 }
])
```

### Product Search

#### Text Search
```javascript
db.products.find({
  $text: { $search: "cordless drill" },
  deleted: false
})
```

#### Category Search
```javascript
db.products.find({
  category_id: "cat_power_tools",
  deleted: false
}).sort({ product_name: 1 })
```

#### Price Range Search
```javascript
db.products.find({
  base_price: { $gte: 50, $lte: 150 },
  deleted: false
}).sort({ base_price: 1 })
```

### Vector Similarity Search

#### Find Similar Products by Image
```javascript
// Requires MongoDB Atlas Vector Search index
db.product_embeddings.aggregate([
  {
    $vectorSearch: {
      index: "vector_image_search",
      path: "image_embedding",
      queryVector: [...],  // 512-dimensional vector from query image
      numCandidates: 100,
      limit: 10
    }
  },
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
    $project: {
      product_id: 1,
      product_name: "$product.product_name",
      sku: "$product.sku",
      base_price: "$product.base_price",
      image_url: 1,
      score: { $meta: "vectorSearchScore" }
    }
  }
])
```

#### Semantic Description Search
```javascript
// Requires MongoDB Atlas Vector Search index
db.product_embeddings.aggregate([
  {
    $vectorSearch: {
      index: "vector_description_search",
      path: "description_embedding",
      queryVector: [...],  // 1536-dimensional vector from query text
      numCandidates: 100,
      limit: 10
    }
  },
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
    $project: {
      product_id: 1,
      product_name: "$product.product_name",
      product_description: "$product.product_description",
      score: { $meta: "vectorSearchScore" }
    }
  }
])
```

### Analytics Queries

#### Sales by Store (Last Year)
```javascript
const oneYearAgo = new Date();
oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

db.orders.aggregate([
  {
    $match: {
      order_date: { $gte: oneYearAgo.toISOString() },
      deleted: false
    }
  },
  {
    $group: {
      _id: "$store_id",
      store_name: { $first: "$store_name" },
      total_orders: { $sum: 1 },
      total_revenue: { $sum: "$total" },
      avg_order_value: { $avg: "$total" }
    }
  },
  { $sort: { total_revenue: -1 } }
])
```

#### Monthly Sales Trend
```javascript
db.orders.aggregate([
  {
    $match: {
      order_date: { $gte: "2024-01-01T00:00:00Z" },
      deleted: false
    }
  },
  {
    $project: {
      month: { $substr: ["$order_date", 0, 7] },  // Extract YYYY-MM
      total: 1
    }
  },
  {
    $group: {
      _id: "$month",
      order_count: { $sum: 1 },
      total_revenue: { $sum: "$total" }
    }
  },
  { $sort: { _id: 1 } }
])
```

---

## Ditto Queries

Ditto uses DQL (Ditto Query Language) which is similar to SQL WHERE clauses.

### Basic Lookups

#### Get Store by ID (Swift)
```swift
let store = try await ditto
  .store.collection("stores")
  .findById(DittoDocumentID(value: "store_seattle"))
  .exec()
```

#### Get Product by SKU (Swift)
```swift
let products = try await ditto
  .store.collection("products")
  .find("sku == 'PWR-DRILL-001'")
  .exec()

if let product = products.first {
  print("Product: \(product["product_name"].stringValue)")
}
```

#### Get Customer by Email (JavaScript)
```javascript
const customers = await ditto
  .store.collection('customers')
  .find("email == 'john.smith@example.com'")
  .exec()

const customer = customers[0]
```

### Inventory Queries

#### Get Inventory for a Store (Swift)
```swift
let inventory = try await ditto
  .store.collection("inventory")
  .find("store_id == 'store_seattle' && deleted == false")
  .exec()
```

#### Low Stock Alert (Swift)
```swift
// Note: Ditto doesn't support computed comparisons ($expr)
// Fetch all inventory and filter in app
let inventory = try await ditto
  .store.collection("inventory")
  .find("store_id == 'store_seattle' && deleted == false")
  .exec()

let lowStock = inventory.filter { doc in
  let stockLevel = doc["stock_level"].intValue
  let reorderThreshold = doc["reorder_threshold"].intValue
  return stockLevel < reorderThreshold
}
```

#### Find Product by Aisle (JavaScript)
```javascript
const inventory = await ditto
  .store.collection('inventory')
  .find("location.aisle == 'A1' && deleted == false")
  .exec()
```

### Order Queries

#### Get Order (Swift)
```swift
let orders = try await ditto
  .store.collection("orders")
  .find("order_id == 'order_20251205_001'")
  .exec()

if let order = orders.first {
  // Get order items separately
  let items = try await ditto
    .store.collection("order_items")
    .find("order_id == '\(order["order_id"].stringValue)'")
    .exec()

  print("Order total: \(order["total"].doubleValue)")
  print("Items: \(items.count)")
}
```

#### Customer Order History (JavaScript)
```javascript
// Get customer's orders
const orders = await ditto
  .store.collection('orders')
  .find(`customer_id == 'cust_456' && deleted == false`)
  .exec()

// Sort in app (Ditto doesn't have ORDER BY yet)
const sortedOrders = orders.sort((a, b) => {
  return b.value.order_date.localeCompare(a.value.order_date)
})

// Take first 10
const recentOrders = sortedOrders.slice(0, 10)
```

### Product Search

#### Category Search (Swift)
```swift
let products = try await ditto
  .store.collection("products")
  .find("category_id == 'cat_power_tools' && deleted == false")
  .exec()

// Sort in app
let sortedProducts = products.sorted {
  $0["product_name"].stringValue < $1["product_name"].stringValue
}
```

#### Price Range Search (JavaScript)
```javascript
const products = await ditto
  .store.collection('products')
  .find("base_price >= 50 && base_price <= 150 && deleted == false")
  .exec()
```

### Subscriptions (Offline Sync)

#### Subscribe to Store's Inventory (Swift)
```swift
// Keep inventory synced for offline use
let subscription = ditto.sync.registerSubscription(
  query: "store_id == 'store_seattle' && deleted == false",
  collection: "inventory"
)

// Cancel when done
subscription.cancel()
```

#### Subscribe to Recent Orders (JavaScript)
```javascript
// Sync orders from last 30 days
const thirtyDaysAgo = new Date()
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

const subscription = ditto.sync.registerSubscription({
  query: `order_date >= '${thirtyDaysAgo.toISOString()}' && deleted == false`,
  collection: 'orders'
})
```

#### Multi-Collection Subscription (Swift)
```swift
// Store manager needs: products, inventory, orders for their store
let storeId = "store_seattle"

// Products (all)
let productsSub = ditto.sync.registerSubscription(
  query: "deleted == false",
  collection: "products"
)

// Inventory (store-specific)
let inventorySub = ditto.sync.registerSubscription(
  query: "store_id == '\(storeId)' && deleted == false",
  collection: "inventory"
)

// Orders (store-specific, last 90 days)
let ninetyDaysAgo = Date().addingTimeInterval(-90 * 24 * 60 * 60)
let ordersSub = ditto.sync.registerSubscription(
  query: "store_id == '\(storeId)' && order_date >= '\(ninetyDaysAgo.ISO8601Format())' && deleted == false",
  collection: "orders"
)
```

### Live Queries (Real-time Updates)

#### Live Inventory Updates (Swift)
```swift
let liveQuery = ditto
  .store.collection("inventory")
  .find("store_id == 'store_seattle' && deleted == false")
  .observeLocal { docs, event in
    switch event {
    case .update(let changes):
      print("Inventory updated: \(changes.insertions.count) added, \(changes.updates.count) modified")
      // Update UI
      self.updateInventoryUI(docs)
    case .initial:
      print("Initial inventory loaded: \(docs.count) items")
      self.updateInventoryUI(docs)
    @unknown default:
      break
    }
  }

// Cancel when done
liveQuery.cancel()
```

#### Live Order Updates (JavaScript)
```javascript
const liveQuery = ditto
  .store.collection('orders')
  .find(`store_id == 'store_seattle' && deleted == false`)
  .observeLocal((docs, event) => {
    if (event.isInitial) {
      console.log(`Initial orders: ${docs.length}`)
    } else {
      console.log(`Orders updated: ${event.insertions.length} new, ${event.updates.length} modified`)
    }

    // Update UI
    updateOrdersUI(docs)
  })

// Cancel when done
liveQuery.stop()
```

---

## Common Use Cases

### Use Case 1: Store Manager Mobile App

**Requirements**:
- View and update inventory for their store
- View orders for their store
- Search products
- Work offline

**Subscriptions**:
```swift
let storeId = UserDefaults.standard.string(forKey: "currentStoreId")!

// Subscribe to relevant data
ditto.sync.registerSubscription(
  query: "deleted == false",
  collection: "products"
)

ditto.sync.registerSubscription(
  query: "store_id == '\(storeId)' && deleted == false",
  collection: "inventory"
)

ditto.sync.registerSubscription(
  query: "store_id == '\(storeId)' && deleted == false",
  collection: "orders"
)
```

**Update Inventory**:
```swift
func updateInventoryStock(productId: String, newStock: Int) async throws {
  let inventoryId = DittoDocumentID(value: [
    "store_id": storeId,
    "product_id": productId
  ])

  try await ditto.store.collection("inventory")
    .findById(inventoryId)
    .update { doc in
      doc?["stock_level"].set(newStock)
      doc?["last_updated"].set(Date().ISO8601Format())
    }
}
```

### Use Case 2: Field Sales Rep Tablet

**Requirements**:
- View customer list
- Create new orders
- View product catalog
- Work offline (sync when online)

**Subscriptions**:
```swift
// Sync assigned customers only
let repId = UserDefaults.standard.string(forKey: "repId")!

ditto.sync.registerSubscription(
  query: "assigned_rep_id == '\(repId)' && deleted == false",
  collection: "customers"
)

// Products (all)
ditto.sync.registerSubscription(
  query: "deleted == false",
  collection: "products"
)
```

**Create Order**:
```swift
func createOrder(
  customerId: String,
  items: [(productId: String, quantity: Int, price: Double)]
) async throws {
  let orderId = "order_\(UUID().uuidString)"

  // Create order
  try await ditto.store.collection("orders").upsert([
    "_id": orderId,
    "order_id": orderId,
    "customer_id": customerId,
    "store_id": "online",
    "order_date": Date().ISO8601Format(),
    "item_count": items.count,
    "total": items.reduce(0) { $0 + $1.quantity * $1.price },
    "status": "pending",
    "deleted": false
  ])

  // Create order items
  for item in items {
    let itemId = UUID().uuidString

    try await ditto.store.collection("order_items").upsert([
      "_id": itemId,
      "order_id": orderId,
      "product_id": item.productId,
      "quantity": item.quantity,
      "unit_price": item.price,
      "line_total": Double(item.quantity) * item.price,
      "deleted": false
    ])
  }
}
```

### Use Case 3: Warehouse Worker App

**Requirements**:
- Find products by location (aisle/shelf)
- Update stock counts
- Generate reorder reports
- Work offline

**Query by Location**:
```swift
func findProductsInAisle(_ aisle: String) async throws -> [DittoDocument] {
  return try await ditto
    .store.collection("inventory")
    .find("location.aisle == '\(aisle)' && deleted == false")
    .exec()
}
```

**Update Stock Count**:
```swift
func updateStockCount(inventoryId: String, newCount: Int) async throws {
  try await ditto.store.collection("inventory")
    .findById(DittoDocumentID(value: inventoryId))
    .update { doc in
      doc?["stock_level"].set(newCount)
      doc?["last_counted"].set(Date().ISO8601Format())
    }
}
```

---

## Performance Optimization

### MongoDB Indexes

Already created by `create_indexes.py`. Key indexes:

```javascript
// Inventory - composite key
{ store_id: 1, product_id: 1 }

// Orders - customer history
{ customer_id: 1, order_date: -1 }

// Order items - order lookup
{ order_id: 1 }

// Products - text search
{ product_name: "text", product_description: "text" }
```

### Ditto Best Practices

1. **Limit Subscriptions**: Only sync data the user needs
   ```swift
   // BAD - syncs all orders
   ditto.sync.registerSubscription(query: "deleted == false", collection: "orders")

   // GOOD - syncs only recent orders for one store
   ditto.sync.registerSubscription(
     query: "store_id == '\(storeId)' && order_date >= '\(recentDate)' && deleted == false",
     collection: "orders"
   )
   ```

2. **Use Specific Queries**: Avoid scanning large datasets
   ```swift
   // BAD - scans all products
   let products = try await ditto.store.collection("products").find("deleted == false").exec()
   let filtered = products.filter { $0["category_id"].stringValue == "cat_power_tools" }

   // GOOD - filters at query level
   let products = try await ditto
     .store.collection("products")
     .find("category_id == 'cat_power_tools' && deleted == false")
     .exec()
   ```

3. **Batch Updates**: Update multiple documents efficiently
   ```swift
   // BAD - N queries
   for productId in productIds {
     try await ditto.store.collection("inventory")
       .findById(DittoDocumentID(value: productId))
       .update { doc in
         doc?["last_counted"].set(Date().ISO8601Format())
       }
   }

   // GOOD - 1 query
   try await ditto.store.collection("inventory")
     .find("product_id IN [\(productIds.joined(separator: ","))]")
     .update { docs in
       for doc in docs {
         doc["last_counted"].set(Date().ISO8601Format())
       }
     }
   ```

4. **Cancel Unused Subscriptions**: Free up resources
   ```swift
   // Store subscriptions to cancel later
   var activeSubscriptions: [DittoSyncSubscription] = []

   func startSync() {
     let sub = ditto.sync.registerSubscription(...)
     activeSubscriptions.append(sub)
   }

   func stopSync() {
     activeSubscriptions.forEach { $0.cancel() }
     activeSubscriptions.removeAll()
   }
   ```

---

## Resources

- **MongoDB Query Documentation**: https://docs.mongodb.com/manual/tutorial/query-documents/
- **Ditto Query Language (DQL)**: https://docs.ditto.live/concepts/querying
- **MongoDB Aggregation**: https://docs.mongodb.com/manual/aggregation/
- **Ditto Swift SDK**: https://docs.ditto.live/sdk/swift/
- **Ditto JavaScript SDK**: https://docs.ditto.live/sdk/javascript/

---

**Last Updated**: 2024-12-07
