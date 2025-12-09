// MongoDB Index Creation Script
// Run with: mongosh <connection_string> --file create_indexes.js
// Or: mongosh and paste this code in the shell

// Use the retail-demo database
db = db.getSiblingDB('retail-demo');

print("\n=== Creating indexes for Zava DIY Retail MongoDB Collections ===\n");

// ============================================================================
// 1. STORES Collection
// ============================================================================
print("Creating indexes for 'stores' collection...");
db.stores.createIndex({ "store_id": 1 }, { unique: true, name: "idx_store_id" });
db.stores.createIndex({ "deleted": 1 }, { name: "idx_deleted" });
db.stores.createIndex({ "is_online": 1 }, { name: "idx_is_online" });
print("✓ stores indexes created\n");

// ============================================================================
// 2. CUSTOMERS Collection
// ============================================================================
print("Creating indexes for 'customers' collection...");
db.customers.createIndex({ "customer_id": 1 }, { unique: true, name: "idx_customer_id" });
db.customers.createIndex({ "email": 1 }, { name: "idx_email" });
db.customers.createIndex({ "primary_store_id": 1 }, { name: "idx_primary_store_id" });
db.customers.createIndex({ "deleted": 1 }, { name: "idx_deleted" });
db.customers.createIndex({ "last_name": 1, "first_name": 1 }, { name: "idx_name" });
print("✓ customers indexes created\n");

// ============================================================================
// 3. CATEGORIES Collection
// ============================================================================
print("Creating indexes for 'categories' collection...");
db.categories.createIndex({ "category_id": 1 }, { unique: true, name: "idx_category_id" });
db.categories.createIndex({ "deleted": 1 }, { name: "idx_deleted" });
print("✓ categories indexes created\n");

// ============================================================================
// 4. PRODUCTS Collection
// ============================================================================
print("Creating indexes for 'products' collection...");
db.products.createIndex({ "product_id": 1 }, { unique: true, name: "idx_product_id" });
db.products.createIndex({ "sku": 1 }, { unique: true, name: "idx_sku" });
db.products.createIndex({ "category_id": 1 }, { name: "idx_category_id" });
db.products.createIndex({ "deleted": 1 }, { name: "idx_deleted" });

// Text search index for product name and description
db.products.createIndex(
  { "product_name": "text", "product_description": "text" },
  { name: "idx_text_search", weights: { product_name: 10, product_description: 5 } }
);
print("✓ products indexes created\n");

// ============================================================================
// 5. PRODUCT_EMBEDDINGS Collection (MongoDB only - not synced to Ditto)
// ============================================================================
print("Creating indexes for 'product_embeddings' collection...");
db.product_embeddings.createIndex({ "product_id": 1 }, { unique: true, name: "idx_product_id" });

// Vector search indexes for AI embeddings
// Note: These require Atlas Search to be enabled on your cluster
// If Atlas Search is not available, these will fail gracefully

try {
  print("  Attempting to create vector search index for image_embedding...");
  // Image embedding vector search (512 dimensions - OpenAI CLIP)
  db.product_embeddings.createSearchIndex({
    name: "vector_image_search",
    definition: {
      mappings: {
        dynamic: false,
        fields: {
          image_embedding: {
            type: "knnVector",
            dimensions: 512,
            similarity: "cosine"
          }
        }
      }
    }
  });
  print("  ✓ Image vector search index created");
} catch (e) {
  print("  ⚠ Image vector search index creation failed (Atlas Search may not be enabled):");
  print("    " + e.message);
}

try {
  print("  Attempting to create vector search index for description_embedding...");
  // Description embedding vector search (1536 dimensions - Azure OpenAI)
  db.product_embeddings.createSearchIndex({
    name: "vector_description_search",
    definition: {
      mappings: {
        dynamic: false,
        fields: {
          description_embedding: {
            type: "knnVector",
            dimensions: 1536,
            similarity: "cosine"
          }
        }
      }
    }
  });
  print("  ✓ Description vector search index created");
} catch (e) {
  print("  ⚠ Description vector search index creation failed (Atlas Search may not be enabled):");
  print("    " + e.message);
}

print("✓ product_embeddings indexes created\n");

// ============================================================================
// 6. INVENTORY Collection
// ============================================================================
print("Creating indexes for 'inventory' collection...");
// Composite key fields (duplicated from _id)
db.inventory.createIndex({ "store_id": 1, "product_id": 1 }, { unique: true, name: "idx_store_product" });
db.inventory.createIndex({ "store_id": 1 }, { name: "idx_store_id" });
db.inventory.createIndex({ "product_id": 1 }, { name: "idx_product_id" });
db.inventory.createIndex({ "deleted": 1 }, { name: "idx_deleted" });

// Low stock alerts
db.inventory.createIndex(
  { "store_id": 1, "stock_level": 1, "reorder_threshold": 1 },
  { name: "idx_low_stock" }
);

// Location-based queries (worker app)
db.inventory.createIndex({ "location.aisle": 1 }, { name: "idx_location_aisle" });
db.inventory.createIndex({ "location.shelf": 1 }, { name: "idx_location_shelf" });

print("✓ inventory indexes created\n");

// ============================================================================
// 7. ORDERS Collection
// ============================================================================
print("Creating indexes for 'orders' collection...");
db.orders.createIndex({ "order_id": 1 }, { unique: true, name: "idx_order_id" });
db.orders.createIndex({ "customer_id": 1 }, { name: "idx_customer_id" });
db.orders.createIndex({ "store_id": 1 }, { name: "idx_store_id" });
db.orders.createIndex({ "order_date": -1 }, { name: "idx_order_date_desc" });
db.orders.createIndex({ "deleted": 1 }, { name: "idx_deleted" });
db.orders.createIndex({ "status": 1 }, { name: "idx_status" });

// Compound indexes for common queries
db.orders.createIndex({ "customer_id": 1, "order_date": -1 }, { name: "idx_customer_orders" });
db.orders.createIndex({ "store_id": 1, "order_date": -1 }, { name: "idx_store_orders" });
db.orders.createIndex({ "store_id": 1, "status": 1 }, { name: "idx_store_status" });

print("✓ orders indexes created\n");

// ============================================================================
// 8. ORDER_ITEMS Collection
// ============================================================================
print("Creating indexes for 'order_items' collection...");
// UUID _id is automatically indexed
db.order_items.createIndex({ "order_id": 1 }, { name: "idx_order_id" });
db.order_items.createIndex({ "product_id": 1 }, { name: "idx_product_id" });
db.order_items.createIndex({ "deleted": 1 }, { name: "idx_deleted" });

// Compound index for order + product lookups
db.order_items.createIndex({ "order_id": 1, "product_id": 1 }, { name: "idx_order_product" });

print("✓ order_items indexes created\n");

// ============================================================================
// Summary
// ============================================================================
print("\n=== Index Creation Summary ===\n");

const collections = [
  'stores',
  'customers',
  'categories',
  'products',
  'product_embeddings',
  'inventory',
  'orders',
  'order_items'
];

collections.forEach(collName => {
  const indexes = db[collName].getIndexes();
  print(`${collName}: ${indexes.length} indexes`);
  indexes.forEach(idx => {
    const keys = Object.keys(idx.key).map(k => `${k}: ${idx.key[k]}`).join(', ');
    print(`  - ${idx.name}: { ${keys} }`);
  });
  print('');
});

print("=== All indexes created successfully! ===\n");
