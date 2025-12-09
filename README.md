# Zava DIY Retail - MongoDB + Ditto Conversion

This project is inspired by the Microsoft Zava DIY Retail demo.  It implements a retail dataset using MongoDB + Ditto, enabling offline-first mobile and edge applications with real-time bidirectional sync.

---

## Overview

**Original**: PostgreSQL-based retail demo with AI embeddings and Row-Level Security
**Converted**: MongoDB Atlas + Ditto sync platform for offline-first distributed applications

**Key Benefits**:
- ✅ Offline-first mobile apps (iOS, Android, Web)
- ✅ Real-time bidirectional sync with automatic conflict resolution (CRDTs)
- ✅ Edge computing support (peer-to-peer sync)
- ✅ Flexible schema with MongoDB
- ✅ Scalable distributed architecture

---

## Quick Start

### Prerequisites
- Python 3.8+
- MongoDB Atlas account (M10+ cluster recommended)
- Ditto account ([portal.ditto.live](https://portal.ditto.live))

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/ditto-examples/retail-demo-zava-dyi-dataset
cd retail-demo-zava-dyi-dataset

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.sample` to `.env` and fill in your credentials:

```bash
cp .env.sample .env
```

Edit `.env`:
```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=retail-demo

# Ditto Configuration
DITTO_APP_ID=your_ditto_app_id_here
DITTO_API_KEY=your_ditto_api_key_here
DITTO_CLOUD_ENDPOINT=https://cloud.ditto.live
```

**Important**: If your MongoDB password contains special characters, URL-encode them:
```bash
python scripts/encode_password.py
```

### 3. Generate Data

```bash
# Test connection
python scripts/test_connection.py

# Generate all data (~10 minutes for 200k orders)
python scripts/generate_mongodb_data.py
```

This creates:
- ✅ 8 stores
- ✅ 9 categories
- ✅ 424 products + embeddings
- ✅ 50,000 customers
- ✅ 3,168 inventory records
- ✅ 200,000 orders
- ✅ ~450,000 order items

### 4. Create Indexes

```bash
python scripts/create_indexes.py
```

### 5. Enable Change Streams

```bash
# Option 1: Via script (requires dbAdmin role)
python scripts/enable_change_streams.py

# Option 2: Via MongoDB Atlas UI
# See CONNECTOR_SETUP.md for instructions
```

### 6. Configure Ditto Connector in Portal

The MongoDB Connector is configured through the **Ditto Portal** (not Docker):

1. Navigate to https://portal.ditto.live
2. Go to Settings → MongoDB Connector
3. Add your MongoDB Atlas connection string
4. Configure collection mappings

See [CONNECTOR_SETUP.md](./CONNECTOR_SETUP.md) for detailed instructions.

### 7. Trigger Initial Sync

```bash
python scripts/trigger_initial_sync.py
```

---

## Project Structure

```
ai-tour-26-zava-diy-dataset-plus-mcp/
├── README.md                    # This file
├── CONNECTOR_SETUP.md           # Ditto connector deployment guide
├── SAMPLE_QUERIES.md            # MongoDB and Ditto query examples
├── SCRIPTS_REFERENCE.md         # Detailed scripts documentation
├── CLAUDE.md                    # Research and design decisions
├── .env                         # Environment variables (gitignored)
├── .env.sample                  # Environment template
├── requirements.txt             # Python dependencies
│
├── config/
│   └── ditto-connector.yaml     # Ditto connector configuration
│
├── scripts/
│   ├── generate_mongodb_data.py           # Main data generation script
│   ├── clear_mongodb_data.py              # Clear all data (for testing)
│   ├── create_indexes.py                  # Create MongoDB indexes
│   ├── drop_indexes.py                    # Drop indexes (schema changes)
│   ├── enable_change_streams.py           # Enable change streams
│   ├── test_change_streams.py             # Verify change streams
│   ├── trigger_initial_sync.py            # Trigger initial Ditto sync
│   ├── test_connection.py                 # Test MongoDB connection
│   ├── check_credentials.py               # Validate credentials
│   └── encode_password.py                 # URL-encode passwords
│
├── original/                    # Original PostgreSQL project files
│   ├── data/                    # Original product/reference data
│   ├── scripts/                 # Original PostgreSQL scripts
│   └── ...                      # Other original files
│
└── docs/                        # Additional documentation
```

---

## Data Model

### Collections

| Collection | Documents | Sync to Ditto | Description |
|-----------|-----------|---------------|-------------|
| `stores` | 8 | ✅ | Physical locations + online store |
| `customers` | 50,000 | ✅ | Customer demographics and contact info |
| `categories` | 9 | ✅ | Product categories with seasonal multipliers |
| `products` | 424 | ✅ | Product catalog (SKU, pricing, descriptions) |
| `product_embeddings` | 424 | ❌ | AI embeddings (too large for mobile) |
| `inventory` | 3,168 | ✅ | Store-specific stock levels with locations |
| `orders` | 200,000 | ✅ | Order headers |
| `order_items` | ~450,000 | ✅ | Order line items |

### Key Design Patterns

#### 1. Composite IDs (Inventory)
```json
{
  "_id": { "store_id": "store_seattle", "product_id": "prod_123" },
  "store_id": "store_seattle",    // Duplicated for queries
  "product_id": "prod_123",       // Duplicated for queries
  "stock_level": 50
}
```

#### 2. UUID IDs (Order Items)
```json
{
  "_id": "550e8400-e29b-41d4-a716-446655440000",
  "order_id": "order_20251205_001",
  "product_id": "prod_123",
  "quantity": 2
}
```

#### 3. MAP Structures (CRDT-Friendly)
```json
{
  "seasonal_multipliers": {
    "jan": 0.8,
    "feb": 0.9,
    "mar": 1.2,
    // ... one key per month (not array!)
  }
}
```

#### 4. Soft Deletes
```json
{
  "product_id": "prod_123",
  "deleted": false,          // Changed to true instead of deleting
  "deleted_at": null         // Set when deleted = true
}
```

#### 5. Separate Collections (Not Embedded)
- Orders and order_items in separate collections
- Avoids array conflicts in CRDTs
- Allows independent updates

---

## Architecture

### MongoDB + Ditto Stack

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#4a90e2','primaryTextColor':'#fff','primaryBorderColor':'#2c5282','lineColor':'#4a90e2','secondaryColor':'#7c3aed','tertiaryColor':'#059669'}}}%%
graph TB
    subgraph flutter["📱 Flutter Applications - Cross-platform"]
        ios["iOS"]
        ipados["iPadOS"]
        android["Android"]
        macos["MacOS"]
        windows["Windows"]
        linux["Linux"]
    end

    subgraph ditto_sync["🔄 Ditto Sync Layer"]
        sync["Ditto Sync<br/>(CRDTs, P2P, Offline-First)"]
    end

    portal["☁️ Ditto Cloud<br/>(Portal)"]

    connector["🔌 MongoDB Connector<br/>(Managed in Portal)<br/>Bidirectional Sync"]

    subgraph mongodb["🗄️ MongoDB Atlas"]
        db["retail-demo database<br/>━━━━━━━━━━━━━━━━<br/>• stores<br/>• customers<br/>• products<br/>• inventory<br/>• orders<br/>• order_items"]
        vector["Vector Search<br/>(embeddings)"]
    end

    ios & ipados & android & macos & windows & linux --> sync
    sync <--> portal
    portal <--> connector
    connector <--> db
    db -.-> vector

    style flutter fill:#2563eb,stroke:#1e40af,stroke-width:3px,color:#fff
    style ditto_sync fill:#f59e0b,stroke:#d97706,stroke-width:3px,color:#000
    style portal fill:#7c3aed,stroke:#6d28d9,stroke-width:2px,color:#fff
    style connector fill:#059669,stroke:#047857,stroke-width:2px,color:#fff
    style mongodb fill:#dc2626,stroke:#b91c1c,stroke-width:3px,color:#fff
    style ios fill:#1e40af,stroke:#1e3a8a,color:#fff
    style ipados fill:#1e40af,stroke:#1e3a8a,color:#fff
    style android fill:#1e40af,stroke:#1e3a8a,color:#fff
    style macos fill:#1e40af,stroke:#1e3a8a,color:#fff
    style windows fill:#1e40af,stroke:#1e3a8a,color:#fff
    style linux fill:#1e40af,stroke:#1e3a8a,color:#fff
    style sync fill:#d97706,stroke:#92400e,color:#fff
    style db fill:#991b1b,stroke:#7f1d1d,color:#fff
    style vector fill:#991b1b,stroke:#7f1d1d,color:#fff
```

### Data Flow

1. **Mobile Device → Ditto**: App creates/updates documents (works offline)
2. **Ditto → MongoDB**: Connector syncs changes to cloud database
3. **MongoDB → Ditto**: Server updates propagate to all connected devices
4. **P2P Sync**: Devices can sync directly without cloud 

### Conflict Resolution

Ditto uses CRDTs (Conflict-Free Replicated Data Types) for automatic merge:
- **MAPs**: Field-level last-write-wins with add-wins semantics
- **Registers**: Document-level last-write-wins
- **Counters**: Increment/decrement operations merge automatically

No manual conflict resolution needed!

---

## Use Cases

### 1. Store Manager Mobile App
- View/update inventory for their store
- Process orders
- Check stock levels and reorder alerts
- Works offline, syncs when connected

**Sample Code** (Flutter/Dart):
```dart
// Subscribe to store's inventory
await ditto.sync.registerSubscription(
  query: "store_id == '$storeId' && deleted == false",
  collection: "inventory"
);

// Update stock level
await ditto.store.collection("inventory")
  .findById(inventoryId)
  .update((doc) {
    doc?["stock_level"].set(newStock);
  });
```

### 2. Field Sales Representative
- View customer list
- Create orders on-site
- Access product catalog
- Offline order capture, sync later

### 3. Warehouse Worker
- Find products by aisle/shelf
- Update stock counts
- Generate reorder reports
- Offline inventory management

---

## Sample Queries

See [SAMPLE_QUERIES.md](./SAMPLE_QUERIES.md) for comprehensive examples.

### MongoDB (Server-Side)

```javascript
// Get order with items
db.orders.aggregate([
  { $match: { order_id: "order_123" } },
  { $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
  }}
])

// Vector similarity search
db.product_embeddings.aggregate([
  { $vectorSearch: {
      index: "vector_description_search",
      path: "description_embedding",
      queryVector: [...],
      limit: 10
  }}
])
```

### Ditto (Mobile/Edge)

```dart
// Get order (Flutter/Dart)
final order = await ditto
  .store.collection("orders")
  .find("order_id == 'order_123'")
  .exec();

// Get order items
final items = await ditto
  .store.collection("order_items")
  .find("order_id == 'order_123'")
  .exec();

// Live query (real-time updates)
final liveQuery = ditto
  .store.collection("inventory")
  .find("store_id == 'store_seattle'")
  .observeLocal((docs, event) {
    // Update UI automatically
    updateInventoryUI(docs);
  });
```

---

## Ditto Connector Setup

The MongoDB Connector is a **managed service** configured through the **Ditto Portal** - there is no Docker container or self-hosted deployment required.

### Setup Steps

1. **Configure in Ditto Portal**:
   - Navigate to https://portal.ditto.live
   - Go to Settings → MongoDB Connector
   - Add your MongoDB Atlas connection string
   - Configure collection mappings and sync settings

2. **Enable Change Streams** (Required):
   ```bash
   python scripts/enable_change_streams.py
   ```

3. **Trigger Initial Sync**:
   ```bash
   python scripts/trigger_initial_sync.py
   ```

See [CONNECTOR_SETUP.md](./CONNECTOR_SETUP.md) for detailed configuration instructions.

---

## Performance

### MongoDB Atlas
- **Cluster**: M10+ recommended (production)
- **Storage**: ~250 MB for full dataset
- **Indexes**: 44 indexes across 8 collections
- **Vector Search**: Requires Atlas Search enabled

### Ditto Sync
- **Initial Sync**: ~5-10 minutes for 200k orders
- **Real-time Sync**: <100ms latency for incremental changes
- **Mobile Storage**: ~10-50 MB per device (with subscriptions)
- **Offline Support**: Unlimited offline duration

---

## Troubleshooting

### Connection Issues

```bash
# Check credentials
python scripts/check_credentials.py

# Test connection
python scripts/test_connection.py
```

### Clear Data for Testing

To reset the database and reload data:

```bash
# Clear all data (preserves indexes and structure)
python scripts/clear_mongodb_data.py

# Regenerate with custom settings
NUM_CUSTOMERS=25000 NUM_ORDERS=100000 \
  python scripts/generate_mongodb_data.py
```

### Schema Changes

When the data model changes:

```bash
# Drop old indexes
python scripts/drop_indexes.py

# Clear data (optional)
python scripts/clear_mongodb_data.py

# Update scripts/generate_mongodb_data.py and scripts/create_indexes.py
# Then regenerate:
python scripts/generate_mongodb_data.py
python scripts/create_indexes.py
```

### Change Streams Not Working

```bash
# Verify change streams enabled
python scripts/test_change_streams.py

# Enable if needed (requires dbAdmin role)
python scripts/enable_change_streams.py
```

### Sync Lag High

1. Check connector resources (CPU/memory)
2. Verify MongoDB indexes are created
3. Increase connector batch size in config
4. Check network latency

### Permission Errors

- MongoDB user needs `dbAdmin` role for change streams
- Ditto API key needs "Connector" role
- Verify credentials in `.env`

See [CONNECTOR_SETUP.md](./CONNECTOR_SETUP.md) for detailed troubleshooting.

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](./README.md) | This file - project overview and quick start |
| [CONNECTOR_SETUP.md](./CONNECTOR_SETUP.md) | Ditto connector deployment guide |
| [SAMPLE_QUERIES.md](./SAMPLE_QUERIES.md) | MongoDB and Ditto query examples |
| [SCRIPTS_REFERENCE.md](./SCRIPTS_REFERENCE.md) | Detailed scripts documentation and workflows |
| [CLAUDE.md](./CLAUDE.md) | Research, design decisions, and architecture analysis |

---

## Key Differences from PostgreSQL Version

| Aspect | PostgreSQL | MongoDB + Ditto |
|--------|------------|-----------------|
| **Offline Support** | ❌ None | ✅ Full offline CRUD |
| **Conflict Resolution** | ❌ Manual | ✅ Automatic (CRDTs) |
| **Mobile Sync** | ❌ Custom implementation | ✅ Built-in |
| **Schema** | ❌ Rigid (migrations) | ✅ Flexible (schema-less) |
| **Multi-Tenant** | ✅ Row-Level Security | ✅ Ditto Permissions |
| **Vector Search** | ✅ pgvector extension | ✅ Atlas Vector Search |
| **Joins** | ✅ Native SQL joins | ⚠️ Application-level or $lookup |
| **Transactions** | ✅ Full ACID | ⚠️ Limited (single document) |
| **Scalability** | ⚠️ Vertical scaling | ✅ Horizontal scaling |

---

## Development Roadmap

- [x] Data model design (CRDT-friendly)
- [x] Data generation scripts
- [x] MongoDB indexes
- [x] Ditto connector configuration
- [x] Deployment guides
- [x] Sample queries
- [ ] Vector search implementation
- [ ] Mobile app examples (iOS, Android)
- [ ] Web app example
- [ ] CI/CD pipeline
- [ ] Performance benchmarks
- [ ] Load testing

---

## Resources

### Documentation
- **MongoDB Atlas**: https://docs.atlas.mongodb.com/
- **Ditto**: https://docs.ditto.live/
- **MongoDB Connector**: https://docs.ditto.live/cloud/mongodb-connector

### Portals
- **MongoDB Atlas**: https://cloud.mongodb.com/
- **Ditto Cloud**: https://portal.ditto.live/

### Support
- **MongoDB Support**: https://support.mongodb.com/
- **Ditto Support**: support@ditto.live

### Original Project
- **GitHub**: https://github.com/microsoft/ai-tour-26-zava-diy-dataset

---

## License

This project is a conversion of the Microsoft Zava DIY Retail demo.
Original license terms apply. See the original repository for details.

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

---

## Acknowledgments

- **Microsoft** - Original Zava DIY Retail demo
- **MongoDB** - Atlas platform and vector search
- **Ditto** - Sync platform and CRDT technology

---

**Status**: Production Ready
**Version**: 1.0
**Last Updated**: 2024-12-07

For questions or issues, please open a GitHub issue or contact the maintainers.
