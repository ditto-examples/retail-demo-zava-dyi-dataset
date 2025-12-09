# Zava DIY Retail - System Architecture

This document describes the complete system architecture for the MongoDB + Ditto conversion of the Zava DIY Retail application.

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Components](#components)
4. [Data Flow](#data-flow)
5. [MongoDB Atlas Configuration](#mongodb-atlas-configuration)
6. [Ditto Cloud Configuration](#ditto-cloud-configuration)
7. [Ditto MongoDB Connector](#ditto-mongodb-connector)
8. [Sync Strategies](#sync-strategies)
9. [Security & Access Control](#security--access-control)
10. [Offline-First Considerations](#offline-first-considerations)
11. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### Architecture Style
**Distributed Edge-First Architecture** with cloud backend

### Key Characteristics
- **Offline-first**: Full CRUD operations work without connectivity
- **Eventually consistent**: CRDTs ensure convergence across peers
- **Cloud-optional**: Devices can sync peer-to-peer or via cloud
- **Multi-tenant**: Store-based access control via Ditto permissions

### Technology Stack

**Cloud (Backend)**:
- MongoDB Atlas (database)
- Ditto Cloud (sync hub)
- Python (data generation, MCP servers)

**Edge (Mobile/Client)**:
- Ditto SDK (local database + sync)
- Flutter/JavaScript (client apps)
- Ditto Query Language (DQL)

**Integration**:
- Ditto MongoDB Connector (bidirectional sync)
- MongoDB Change Streams (change detection)
- MCP Servers (AI integration via Claude)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cloud Layer                              │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │   MongoDB    │◄────────┤    Ditto     │                     │
│  │    Atlas     │  Change │  MongoDB     │                     │
│  │              │  Streams│  Connector   │                     │
│  │  - 9 Collections       │              │                     │
│  │  - Indexes            │  - ID Mapping │                     │
│  │  - Vector Search      │  - CRDTs      │                     │
│  └──────┬───────┘         └──────┬───────┘                     │
│         │                        │                               │
│         │                        │                               │
│    ┌────▼─────┐            ┌────▼─────┐                        │
│    │  Python  │            │  Ditto   │                        │
│    │   Data   │            │  Cloud   │                        │
│    │Generator │            │  Portal  │                        │
│    └──────────┘            └──┬───┬───┘                        │
│                               │   │                              │
└───────────────────────────────┼───┼──────────────────────────────┘
                                │   │
                    ┌───────────┘   └───────────┐
                    │                           │
         ┌──────────▼──────────┐     ┌──────────▼──────────┐
         │   Sync Protocol     │     │   Sync Protocol     │
         │  (CRDT Delta Sync)  │     │  (CRDT Delta Sync)  │
         └──────────┬──────────┘     └──────────┬──────────┘
                    │                           │
┌───────────────────┼───────────────────────────┼──────────────────┐
│                   │     Edge Layer            │                   │
│                   │                           │                   │
│    ┌──────────────▼───────┐    ┌─────────────▼──────────┐       │
│    │  Mobile POS Device   │    │  Sales Rep Tablet      │       │
│    │                      │    │                         │       │
│    │  ┌────────────────┐  │    │  ┌────────────────┐    │       │
│    │  │  Ditto Store   │  │    │  │  Ditto Store   │    │       │
│    │  │  (Local DB)    │  │    │  │  (Local DB)    │    │       │
│    │  │                │  │    │  │                │    │       │
│    │  │ - orders       │  │    │  │ - customers    │    │       │
│    │  │ - order_items  │  │    │  │ - products     │    │       │
│    │  │ - inventory    │  │    │  │ - orders       │    │       │
│    │  │ - products     │  │    │  └────────────────┘    │       │
│    │  └────────────────┘  │    │                         │       │
│    │                      │    │  Subscriptions:         │       │
│    │  Subscriptions:      │    │  - All products         │       │
│    │  - store_id='seattle'│    │  - Customer assigned   │       │
│    └──────────────────────┘    └─────────────────────────┘       │
│                                                                   │
│    ┌──────────────────────────────────────────────────────┐     │
│    │           Peer-to-Peer Sync (Optional)               │     │
│    │  Devices can sync directly via WiFi/Bluetooth        │     │
│    └──────────────────────────────────────────────────────┘     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Integration Layer                           │
│                                                                  │
│    ┌──────────────┐         ┌──────────────┐                   │
│    │     MCP      │         │    Azure     │                   │
│    │   Servers    │         │   OpenAI     │                   │
│    │              │         │              │                   │
│    │ - Customer   │         │ - Embeddings │                   │
│    │   Sales      │         │ - text-embed │                   │
│    │ - Sales      │         │   -3-small   │                   │
│    │   Analysis   │         │              │                   │
│    └──────────────┘         └──────────────┘                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. MongoDB Atlas

**Role**: Primary cloud database

**Responsibilities**:
- Store all 9 collections (~453K documents)
- Provide vector search for embeddings
- Enable Change Streams for Ditto connector
- Support complex analytics queries
- Maintain indexes for performance

**Configuration**:
- **Cluster**: M10+ (recommended for Change Streams)
- **Region**: US (closest to users)
- **Backup**: Point-in-time recovery enabled
- **Change Streams**: Pre/post images enabled
- **Vector Search**: Atlas Search indexes configured

### 2. Ditto Cloud

**Role**: Sync coordination hub

**Responsibilities**:
- Coordinate sync between mobile devices
- Store transient sync state
- Route messages between peers
- Enforce permissions
- Provide web dashboard

**Configuration**:
- **App ID**: Unique identifier for application
- **Authentication**: API key-based
- **Collections**: 8 synced (excludes product_embeddings)
- **Permissions**: Store-based access control

### 3. Ditto MongoDB Connector

**Role**: Bidirectional sync between MongoDB and Ditto

**How It Works**:
1. **MongoDB → Ditto**: Listens to Change Streams, converts to CRDT operations
2. **Ditto → MongoDB**: Receives CRDT updates, writes to MongoDB
3. **Conflict Resolution**: CRDT merge logic (automatic, no manual intervention)
4. **Delta Sync**: Only changes transmitted (not full documents)

**Configuration**: See [Ditto MongoDB Connector](#ditto-mongodb-connector) section

### 4. Mobile/Edge Devices

**Role**: Offline-first clients

**Capabilities**:
- Full CRUD operations offline
- Local Ditto Store (embedded database)
- Subscription-based sync
- Peer-to-peer sync (optional)
- Conflict-free updates (CRDTs)

**Device Types**:
- **POS Terminals**: Store-specific data (inventory, orders)
- **Sales Tablets**: Customer-focused (products, order history)
- **Manager Devices**: Multi-store analytics

### 5. MCP Servers

**Role**: AI integration for Claude Code

**Servers**:
1. **customer_sales_mongodb.py**: Product search, semantic queries
2. **sales_analysis_mongodb.py**: Analytics, reporting

**Functionality**:
- Query MongoDB directly (not via Ditto)
- Support vector similarity search
- Provide natural language interfaces

### 6. Data Generation Pipeline

**Role**: Generate realistic retail dataset

**Components**:
- **generate_zava_mongodb.py**: Main generator
- **transform_*.py**: Data transformation scripts
- **Faker**: Realistic names, emails, phones
- **Azure OpenAI**: Generate embeddings

---

## Data Flow

### Write Flow: Mobile → Cloud

```
1. Mobile Device
   └─> Ditto Store (local write)
       └─> CRDT operation recorded

2. Ditto SDK
   └─> Sync protocol (delta transmission)
       └─> Ditto Cloud

3. Ditto Cloud
   └─> Merge CRDTs from multiple peers
       └─> Ditto MongoDB Connector

4. MongoDB Connector
   └─> Convert CRDT → MongoDB document
       └─> MongoDB Atlas (write via driver)

5. MongoDB Atlas
   └─> Document updated
       └─> Change Stream event emitted
```

### Read Flow: Cloud → Mobile

```
1. MongoDB Atlas
   └─> Document changed (via app, connector, or manual edit)
       └─> Change Stream event

2. Ditto MongoDB Connector
   └─> Detect change event
       └─> Convert to CRDT operation

3. Ditto Cloud
   └─> Distribute to subscribed peers
       └─> Sync protocol (delta transmission)

4. Mobile Device
   └─> Receive CRDT delta
       └─> Merge into Ditto Store (local)
       └─> UI updates automatically (reactive queries)
```

### Query Flow: Mobile Device

**Offline** (no connectivity):
```
App Query
 └─> Ditto Store (local query)
     └─> Return local data
         └─> UI renders
```

**Online** (with connectivity):
```
App Query
 └─> Ditto Store (local query, immediate response)
     └─> Return local data
         └─> UI renders

Background Sync (parallel)
 └─> Ditto Cloud
     └─> Fetch updates
         └─> Merge into local store
             └─> UI auto-updates if data changed
```

### Peer-to-Peer Sync (Optional)

```
Device A (offline)         Device B (offline)
    │                           │
    └─────> WiFi/Bluetooth <────┘
                  │
                  ▼
          CRDT Delta Exchange
                  │
         ┌────────┴────────┐
         ▼                 ▼
    Device A          Device B
    (updated)         (updated)
         │                 │
         └─────────────────┘
                  │
                  ▼
         Both sync to cloud later
         (conflicts already resolved)
```

---

## MongoDB Atlas Configuration

### Cluster Setup

**Recommended Tier**: M10 or higher
- **Reason**: Change Streams require replica sets (M10+)
- **Storage**: ~1 GB (current), plan for growth
- **RAM**: 2-4 GB (handles indexes and aggregations)

### Database Configuration

**Database Name**: `zava`

**Collections**: 9 total
```
zava
├── stores
├── customers
├── categories
├── product_types
├── products
├── product_embeddings
├── inventory
├── orders
└── order_items
```

### Change Streams Configuration

**Enable Pre/Post Images**:
```javascript
db.runCommand({
  collMod: "orders",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "order_items",
  changeStreamPreAndPostImages: { enabled: true }
})

// Repeat for all synced collections
```

**Why Required**:
- Ditto connector needs full document state (not just delta)
- Pre-image: document before change
- Post-image: document after change

### Vector Search Configuration

**Create Vector Index** (product_embeddings):
```json
{
  "name": "vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "image_embedding",
        "numDimensions": 512,
        "similarity": "cosine"
      },
      {
        "type": "vector",
        "path": "description_embedding",
        "numDimensions": 1536,
        "similarity": "cosine"
      }
    ]
  }
}
```

**Access**: Via Atlas UI → Search → Create Index

### User Permissions

**Application User**:
```javascript
{
  "user": "zava_app_user",
  "pwd": "<secure_password>",
  "roles": [
    { "role": "readWrite", "db": "zava" },
    { "role": "changeStream", "db": "zava" }
  ]
}
```

**Read-Only User** (for analytics):
```javascript
{
  "user": "zava_readonly",
  "pwd": "<secure_password>",
  "roles": [
    { "role": "read", "db": "zava" }
  ]
}
```

### Connection String Format

```
mongodb+srv://zava_app_user:<password>@cluster.mongodb.net/zava?retryWrites=true&w=majority
```

**Environment Variable** (`.env`):
```bash
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=zava
```

---

## Ditto Cloud Configuration

### Application Setup

**Create App**:
1. Sign up at https://portal.ditto.live
2. Create new application: "Zava Retail"
3. Note App ID and API key

**App Configuration**:
```yaml
app_name: zava-retail
app_id: <your_app_id>
permissions: store-based
auth_mode: online_with_authentication
```

### Permissions Configuration

**Store-Based Access Control**:
```json
{
  "rules": [
    {
      "collection": "inventory",
      "operations": ["read", "update"],
      "condition": "store_id = $user.store_id"
    },
    {
      "collection": "orders",
      "operations": ["read", "write"],
      "condition": "store_id = $user.store_id"
    },
    {
      "collection": "order_items",
      "operations": ["read", "write"],
      "condition": "order_id IN (SELECT order_id FROM orders WHERE store_id = $user.store_id)"
    },
    {
      "collection": "products",
      "operations": ["read"],
      "condition": "deleted = false"
    },
    {
      "collection": "customers",
      "operations": ["read", "write"],
      "condition": "primary_store_id = $user.store_id"
    }
  ],
  "super_manager": {
    "rls_user_id": "00000000-0000-0000-0000-000000000000",
    "permissions": "all"
  }
}
```

**Permission Types**:
- **read**: Query data
- **write**: Create, update (respecting CRDTs)
- **delete**: Soft delete (set deleted=true)

### Collections to Sync

**Synced Collections** (8):
- stores
- customers
- categories
- product_types
- products
- inventory
- orders
- order_items

**NOT Synced** (1):
- product_embeddings (too large, MongoDB-only)

---

## Ditto MongoDB Connector

### Connector Configuration

**File**: `config/ditto_connector_config.yaml`

```yaml
connector_version: 1.0
mongodb:
  connection_string: ${MONGODB_CONNECTION_STRING}
  database: zava

ditto:
  app_id: ${DITTO_APP_ID}
  api_key: ${DITTO_API_KEY}
  endpoint: https://cloud.ditto.live

collections:
  - name: stores
    id_mapping:
      mode: single_field
      field: store_id
    sync_enabled: true

  - name: customers
    id_mapping:
      mode: single_field
      field: customer_id
    sync_enabled: true

  - name: categories
    id_mapping:
      mode: match_ids
    sync_enabled: true

  - name: product_types
    id_mapping:
      mode: match_ids
    sync_enabled: true

  - name: products
    id_mapping:
      mode: single_field
      field: product_id
    sync_enabled: true

  - name: product_embeddings
    sync_enabled: false  # NOT synced to Ditto

  - name: inventory
    id_mapping:
      mode: multiple_fields
      fields: [store_id, product_id]
    sync_enabled: true

  - name: orders
    id_mapping:
      mode: single_field
      field: order_id
    sync_enabled: true

  - name: order_items
    id_mapping:
      mode: match_ids  # UUID-based
    sync_enabled: true

settings:
  initial_sync: true
  rate_limit_per_second: 100
  batch_size: 1000
  retry_strategy:
    max_retries: 3
    backoff_multiplier: 2
```

### ID Mapping Modes Explained

**1. match_ids** (MongoDB _id = Ditto _id):
```json
// MongoDB
{ "_id": "cat_power_tools", "category_id": "cat_power_tools", ... }

// Ditto
{ "_id": "cat_power_tools", "category_id": "cat_power_tools", ... }
```

**2. single_field** (Map one field → Ditto _id):
```json
// MongoDB
{ "_id": ObjectId("..."), "customer_id": "cust_123", ... }

// Ditto
{ "_id": "cust_123", "customer_id": "cust_123", ... }
```

**3. multiple_fields** (Composite key):
```json
// MongoDB
{ "_id": { "store_id": "seattle", "product_id": "drill" }, "store_id": "seattle", "product_id": "drill", ... }

// Ditto
{ "_id": { "store_id": "seattle", "product_id": "drill" }, "store_id": "seattle", "product_id": "drill", ... }
```

### Conflict Resolution Strategy

**CRDTs (Conflict-Free Replicated Data Types)**:
- **REGISTER** (last-write-wins): Scalar fields (name, price, quantity)
- **MAP** (add-wins): Nested objects (specifications, location)
- **Version Vectors**: Track causality across peers

**Example Conflict**:
```
Device A (offline): product.base_price = 149.99
Device B (offline): product.base_price = 159.99

On sync:
  - Version vectors compared
  - Last-write-wins (based on timestamp)
  - Final value: 159.99 (B's timestamp is later)
```

**No Conflict (Independent Fields)**:
```
Device A (offline): product.base_price = 149.99
Device B (offline): product.stock_level = 50

On sync:
  - Both updates applied
  - Final: { base_price: 149.99, stock_level: 50 }
```

### Initial Sync

**Process**:
1. Connector reads all documents from MongoDB
2. Converts to Ditto format (ID mapping applied)
3. Uploads to Ditto Cloud (rate-limited)
4. Background process (non-blocking)

**Time Estimate**:
- 200K orders @ 500B = 100MB
- Rate: 100 docs/second
- Duration: ~33 minutes

**Incremental Sync** (after initial):
- Only changed documents
- Near real-time (<1 second latency)

---

## Sync Strategies

### Subscription-Based Sync

**Principle**: Devices only sync data they need

**Store Manager** (1 store):
```swift
ditto.sync.registerSubscription(
  query: "SELECT * FROM inventory WHERE store_id = :storeId",
  arguments: ["storeId": "store_seattle"]
)
ditto.sync.registerSubscription(
  query: "SELECT * FROM orders WHERE store_id = :storeId",
  arguments: ["storeId": "store_seattle"]
)
ditto.sync.registerSubscription(
  query: "SELECT * FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE store_id = :storeId)",
  arguments: ["storeId": "store_seattle"]
)
```

**Sales Rep** (100 customers):
```swift
let customerIds = ["cust_1", "cust_2", "cust_3"]

ditto.sync.registerSubscription(
  query: "SELECT * FROM customers WHERE customer_id IN :customerIds",
  arguments: ["customerIds": customerIds]
)
ditto.sync.registerSubscription(
  query: "SELECT * FROM orders WHERE customer_id IN :customerIds",
  arguments: ["customerIds": customerIds]
)
```

**Product Catalog** (all products):
```swift
ditto.sync.registerSubscription(
  query: "SELECT * FROM products WHERE deleted = false"
)
ditto.sync.registerSubscription(
  query: "SELECT * FROM categories WHERE deleted = false"
)
```

### Sync Optimizations

**Delta Sync**:
- Only changed fields transmitted
- CRDT operations are compact (~100-500 bytes)

**Compression**:
- Ditto automatically compresses sync traffic
- Typical: 70-80% compression ratio

**Background Sync**:
- Sync happens in background threads
- Exponential backoff on failure
- Automatic retry with jitter

**Bandwidth Management**:
```swift
ditto.sync.config.maxBytesPerSecond = 100_000  // 100 KB/s
ditto.sync.config.pauseOnMetered = false
ditto.sync.config.preferPeerToPeer = true
```

---

## Security & Access Control

### Multi-Tenant Isolation

**Store-Based Tenancy**:
- Each store has unique `rls_user_id`
- Ditto permissions filter by `store_id`
- Store managers only see their store's data

**Super Manager Access**:
- `rls_user_id = "00000000-0000-0000-0000-000000000000"`
- Bypasses all permission filters
- Used for admin operations, analytics

### Authentication Flow

```
1. User Login
   └─> App validates credentials (custom auth)
       └─> Retrieve store_id, rls_user_id

2. Ditto Initialization
   └─> ditto.setIdentity(userId: rls_user_id)
       └─> Authenticate with Ditto Cloud

3. Permission Enforcement
   └─> All queries filtered by permissions
       └─> Server-side validation (cannot bypass)

4. Data Access
   └─> Subscriptions apply permission filters automatically
```

### Credential Management

**Environment Variables** (`.env`):
```bash
# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE=zava

# Ditto
DITTO_APP_ID=your_app_id
DITTO_API_KEY=your_api_key

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=your_key
```

**Never Commit**:
- `.env` file (in .gitignore)
- API keys, passwords, connection strings

**Always Commit**:
- `.env.sample` (template with no secrets)

---

## Offline-First Considerations

### Device Capabilities Offline

**Full CRUD Operations**:
- ✅ Create orders
- ✅ Update inventory
- ✅ Query products
- ✅ Search customers

**Limitations**:
- ❌ Vector search (requires embeddings, cloud-only)
- ❌ Complex aggregations (limited by local resources)

### Conflict Scenarios

**Scenario 1: Concurrent Inventory Updates**
```
Store A (offline): Product X stock = 50 (was 45)
Store B (offline): Product X stock = 40 (was 45)

Resolution:
  - Separate inventory documents per store
  - _id: { store_id: "A", product_id: "X" }
  - _id: { store_id: "B", product_id: "X" }
  - No conflict (different documents)
```

**Scenario 2: Customer Name Change**
```
Device A (offline): customer.first_name = "Johnny"
Device B (offline): customer.first_name = "Jonathan"

Resolution:
  - Last-write-wins (REGISTER type)
  - Version vectors determine latest
  - Final: "Jonathan" (Device B timestamp later)
```

**Scenario 3: Order Creation**
```
Device A (offline): Creates order_001 with 2 items
Device B (offline): Creates order_002 with 3 items

Resolution:
  - No conflict (different order IDs, UUIDs ensure uniqueness)
  - Both orders synced successfully
```

### Sync Recovery Strategies

**Exponential Backoff**:
```
Attempt 1: Immediate
Attempt 2: 1 second delay
Attempt 3: 2 seconds delay
Attempt 4: 4 seconds delay
Attempt 5: 8 seconds delay
```

**Jitter**: Random delay added to prevent thundering herd

**Persistence**: Sync queue persisted to disk (survives app restart)

---

## Deployment Architecture

### Development Environment

```
Docker Compose
├── MongoDB (local container)
│   └── Port 27017
├── Ditto Local (optional)
│   └── Port 8080
└── Python (data generator)
    └── Connects to local or Atlas
```

### Staging Environment

```
Cloud Resources
├── MongoDB Atlas (M10 cluster, staging)
├── Ditto Cloud (staging app)
└── Test Devices (iOS/Android simulators)
```

### Production Environment

```
Cloud Resources
├── MongoDB Atlas (M30+ cluster, multi-region)
│   ├── Primary Region: US-West
│   ├── Secondary Region: US-East (failover)
│   └── Backup: Continuous, 7-day retention
├── Ditto Cloud (production app)
│   ├── Global CDN
│   ├── Multi-region sync hubs
│   └── 99.9% uptime SLA
└── Mobile Devices (thousands)
    ├── POS terminals
    ├── Sales tablets
    └── Manager apps
```

### Monitoring & Observability

**MongoDB Atlas**:
- Performance Advisor (index recommendations)
- Real-time metrics (queries/sec, connections)
- Alerts (high CPU, low disk space)

**Ditto Cloud**:
- Sync dashboard (active devices, data transferred)
- Error logs (failed syncs, conflicts)
- Latency metrics (sync lag time)

**Application**:
- Error tracking (Sentry, Datadog)
- Usage analytics (device activity, feature usage)
- Performance monitoring (query times, sync speed)

---

## Summary

This architecture provides:
- ✅ **Offline-first**: Full functionality without connectivity
- ✅ **Scalable**: Cloud handles analytics, edge handles real-time
- ✅ **Resilient**: CRDTs eliminate manual conflict resolution
- ✅ **Secure**: Multi-tenant isolation via permissions
- ✅ **Performant**: Local queries instant, sync in background

**Next Steps**:
1. Set up MongoDB Atlas cluster
2. Configure Ditto Cloud app
3. Deploy MongoDB Connector
4. Generate data
5. Test sync between devices

---

**Document Version**: 1.0
**Last Updated**: 2024-12-05
**Next**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for PostgreSQL conversion details
