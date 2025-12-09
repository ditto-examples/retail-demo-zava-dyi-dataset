# Ditto MongoDB Connector - Setup Guide

This guide walks through configuring the Ditto MongoDB Connector for the Zava Retail demo application.

**Important**: The MongoDB Connector is a **managed service** configured through the Ditto Portal. 

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Enable MongoDB Change Streams](#enable-mongodb-change-streams)
3. [Configure Connector in Portal](#configure-connector-in-portal)
4. [Collection Configuration](#collection-configuration)
5. [Initial Data Sync](#initial-data-sync)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- ✅ MongoDB Atlas cluster (M10+ recommended for Change Streams)
- ✅ MongoDB 4.4+ with Change Streams support
- ✅ Ditto account with app created (https://portal.ditto.live)
- ✅ Network connectivity between Ditto Cloud and MongoDB Atlas

### Environment Variables
Ensure these are set in `.env` for local scripts:

```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=retail-demo

# Ditto Configuration
DITTO_APP_ID=your_ditto_app_id_here
DITTO_API_KEY=your_ditto_api_key_here
DITTO_CLOUD_ENDPOINT=https://cloud.ditto.live
```

**Note**: URL-encode special characters in your MongoDB password:
```bash
python scripts/encode_password.py
```

---

## Enable MongoDB Change Streams

Change Streams are **required** for the Ditto connector to capture real-time changes.

### Step 1: Enable Pre and Post Images

Run this script to enable change streams on all collections:

```bash
python scripts/enable_change_streams.py
```

Or manually via `mongosh`:

```javascript
// Connect to MongoDB
use retail-demo

// Enable change streams for each collection
db.runCommand({
  collMod: "stores",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "customers",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "categories",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "products",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "inventory",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "orders",
  changeStreamPreAndPostImages: { enabled: true }
})

db.runCommand({
  collMod: "order_items",
  changeStreamPreAndPostImages: { enabled: true }
})
```

### Step 2: Verify Change Streams

Test that change streams are working:

```bash
python scripts/test_change_streams.py
```

Expected output:
```
✅ Change streams enabled on all collections
✅ Watching for changes (insert a document to test)
```

---

## Configure Connector in Portal

### Step 1: Access Ditto Portal

1. Navigate to https://portal.ditto.live
2. Log in to your account
3. Select your app (or create a new one)

### Step 2: Navigate to MongoDB Connector Settings

1. Click on **Settings** in the left sidebar
2. Select **MongoDB Connector**
3. Click **Add New Connector** (if first time)

### Step 3: Add MongoDB Connection

Enter your MongoDB Atlas connection details:

```
Connection String: mongodb+srv://username:password@cluster.mongodb.net/
Database Name: retail-demo
```

**Important**:
- Ensure your MongoDB user has `readWrite` and `changeStream` roles
- Whitelist Ditto Cloud IP addresses in MongoDB Atlas Network Access
- Test the connection using the "Test Connection" button in the Portal

### Step 4: Configure Collection Mappings

Configure ID mappings for each collection:

#### stores
```yaml
Collection: stores
ID Mapping Mode: single_field
ID Field: store_id
Sync Enabled: true
```

#### customers
```yaml
Collection: customers
ID Mapping Mode: single_field
ID Field: customer_id
Sync Enabled: true
```

#### categories
```yaml
Collection: categories
ID Mapping Mode: match_ids
Sync Enabled: true
```

#### products
```yaml
Collection: products
ID Mapping Mode: single_field
ID Field: product_id
Sync Enabled: true
```

#### product_embeddings
```yaml
Collection: product_embeddings
Sync Enabled: false
Reason: Too large for mobile devices (16-20KB per doc)
```

#### inventory
```yaml
Collection: inventory
ID Mapping Mode: match_ids
Sync Enabled: true
Notes: Uses UUID _id
```

#### orders
```yaml
Collection: orders
ID Mapping Mode: single_field
ID Field: order_id
Sync Enabled: true
```

#### order_items
```yaml
Collection: order_items
ID Mapping Mode: match_ids
Sync Enabled: true
Notes: Uses UUID _id
```

### Step 5: Configure Sync Settings

In the Portal, configure these advanced settings:

- **Batch Size**: 100-500 documents per sync batch
- **Sync Frequency**: Real-time (based on Change Streams)
- **Conflict Resolution**: CRDT-based (automatic)
- **Error Handling**: Retry with exponential backoff

### Step 6: Enable Connector

1. Review all collection configurations
2. Click **Save Configuration**
3. Click **Enable Connector**
4. Monitor the status - should show "Running" within 30 seconds

---

## Collection Configuration

### ID Mapping Modes Explained

**1. match_ids (1:1 Mapping)**
- MongoDB `_id` = Ditto `_id` (identical values)
- Used for: categories, inventory, order_items
- Example:
  ```json
  MongoDB: { "_id": "550e8400-...", "product_id": "prod_123" }
  Ditto:   { "_id": "550e8400-...", "product_id": "prod_123" }
  ```

**2. single_field (Field → _id)**
- Map one MongoDB field to Ditto `_id`
- Used for: stores, customers, products, orders
- Example:
  ```json
  MongoDB: { "_id": ObjectId("..."), "customer_id": "cust_456" }
  Ditto:   { "_id": "cust_456", "customer_id": "cust_456" }
  ```

**3. multiple_fields (Composite Key)**
- Not used in this project (replaced with UUID approach)

### Why Duplicate ID Fields?

All collections have ID fields duplicated in the document body:

```json
{
  "_id": "prod_123",
  "product_id": "prod_123",  // Duplicated for Ditto queries
  "name": "Drill"
}
```

**Reason**: Enables Ditto permission scoping and simpler queries:
```dart
// Can query by product_id in Ditto
ditto.store.collection("products")
  .find("product_id == 'prod_123'")
```

---

## Initial Data Sync

After enabling the connector, trigger an initial sync for existing data:

### Step 1: Trigger Initial Sync

The connector only syncs **new changes** detected via Change Streams. To sync existing data:

```bash
python scripts/trigger_initial_sync.py
```

This script:
1. Touches all documents by updating a timestamp field
2. Triggers Change Stream events
3. Connector picks up the changes and syncs to Ditto

**Expected Duration**: 5-10 minutes for 200K+ documents

### Step 2: Monitor Sync Progress

In the Ditto Portal:
1. Go to **Settings → MongoDB Connector**
2. View **Sync Statistics**:
   - Documents synced
   - Sync lag (should be <10 seconds after initial load)
   - Error count (should be 0)

### Step 3: Verify Data in Ditto

Use the Ditto Portal Data Browser:
1. Navigate to **Data Browser**
2. Select collections (stores, customers, products, etc.)
3. Verify document counts match MongoDB:

```bash
# MongoDB
db.stores.countDocuments({})        # Should be 8
db.customers.countDocuments({})     # Should be 50,000
db.products.countDocuments({})      # Should be 424
db.inventory.countDocuments({})     # Should be 3,168
db.orders.countDocuments({})        # Should be 200,000
db.order_items.countDocuments({})   # Should be 400,000+
```

---

## Monitoring

### Portal Dashboard

The Ditto Portal provides real-time monitoring:

**Sync Status**:
- ✅ Running / ❌ Stopped / ⚠️ Error
- Last sync timestamp
- Sync lag (time behind MongoDB)

**Metrics**:
- Documents synced (total)
- Sync operations per second
- Error rate
- Bandwidth usage

**Logs**:
- View connector logs directly in Portal
- Filter by severity (info, warning, error)
- Search logs by collection or document ID

### Health Checks

Monitor connector health in Portal:
- Green: All collections syncing normally
- Yellow: Some collections experiencing delays
- Red: Connector stopped or critical errors

### Alerts

Configure alerts in Portal:
- Sync lag > threshold (e.g., 60 seconds)
- Error rate > threshold (e.g., 1%)
- Connector stopped unexpectedly

---

## Troubleshooting

### Common Issues

#### 1. Connection Failed

**Error**: "Failed to connect to MongoDB"

**Solutions**:
- Verify MongoDB connection string is correct
- Check MongoDB user has `readWrite` and `changeStream` roles
- Whitelist Ditto Cloud IP addresses in MongoDB Atlas Network Access
- Test connection string locally:
  ```bash
  python scripts/test_connection.py
  ```

#### 2. Change Streams Not Working

**Error**: "Change streams not enabled"

**Solutions**:
- Run `python scripts/enable_change_streams.py`
- Verify MongoDB cluster is M10+ (required for Change Streams)
- Check MongoDB version is 4.4+ (minimum for change stream support)
- Test change streams:
  ```bash
  python scripts/test_change_streams.py
  ```

#### 3. Documents Not Syncing

**Error**: Documents exist in MongoDB but not in Ditto

**Solutions**:
- Trigger initial sync: `python scripts/trigger_initial_sync.py`
- Check collection is enabled in Portal configuration
- Verify ID mapping mode is correct for the collection
- Check for ID field presence (must be non-null, top-level)

#### 4. High Sync Lag

**Error**: Sync lag > 60 seconds

**Solutions**:
- Check MongoDB indexes are created: `python scripts/create_indexes.py`
- Increase batch size in Portal settings (100 → 500)
- Verify network connectivity between Ditto Cloud and MongoDB Atlas
- Check MongoDB cluster performance metrics

#### 5. Permission Denied Errors

**Error**: "User does not have changeStream privileges"

**Solutions**:
- Grant `changeStream` role to MongoDB user:
  ```javascript
  use admin
  db.grantRolesToUser("your_username", [
    { role: "readWrite", db: "retail-demo" },
    { role: "changeStream", db: "retail-demo" }
  ])
  ```

#### 6. Duplicate ID Errors

**Error**: "Duplicate _id found"

**Solutions**:
- Ensure ID fields are unique in MongoDB
- Check ID mapping mode matches data structure
- For composite IDs, verify all key fields are present and non-null

### Debug Mode

Enable debug logging in Portal:
1. Settings → MongoDB Connector
2. Advanced Settings
3. Log Level: DEBUG
4. Save and restart connector

View detailed logs in Portal to diagnose issues.

### Support Resources

- **Ditto Documentation**: https://docs.ditto.live/cloud/mongodb-connector
- **Ditto Support**: support@ditto.live
- **MongoDB Atlas Support**: https://support.mongodb.com/

---

## Advanced Configuration

### Selective Sync (Filters)

Configure sync filters in Portal to reduce data volume:

**Example**: Only sync active customers
```json
{
  "collection": "customers",
  "filter": { "deleted": false, "active": true }
}
```

### Custom Transformations

Configure field transformations in Portal:

**Example**: Convert timestamps
```json
{
  "collection": "orders",
  "transformations": {
    "order_date": "toISOString"
  }
}
```

### Performance Tuning

Optimize sync performance in Portal settings:
- **Batch Size**: 100-500 (lower = more real-time, higher = better throughput)
- **Parallel Streams**: 1-5 (number of concurrent change streams)
- **Buffer Size**: 1000-10000 (documents buffered before sync)

---

## Security Best Practices

### MongoDB User Permissions

Create a dedicated MongoDB user for the connector with minimal permissions:

```javascript
use admin
db.createUser({
  user: "ditto_connector",
  pwd: "strong_password_here",
  roles: [
    { role: "readWrite", db: "retail-demo" },
    { role: "changeStream", db: "retail-demo" }
  ]
})
```

### Network Security

- ✅ Use MongoDB Atlas Network Access whitelist
- ✅ Enable SSL/TLS for MongoDB connections
- ✅ Use strong passwords and rotate regularly
- ✅ Enable MongoDB Atlas encryption at rest
- ✅ Use Ditto's managed infrastructure (no self-hosted security concerns)

### API Key Management

- ✅ Store Ditto API keys securely (not in code)
- ✅ Use environment variables or secrets management
- ✅ Rotate API keys periodically
- ✅ Use different API keys for dev/staging/production

---

## Checklist: Connector Setup

Use this checklist to verify setup:

- [ ] MongoDB Atlas cluster created (M10+)
- [ ] MongoDB user created with readWrite + changeStream roles
- [ ] Change streams enabled on all collections
- [ ] Change streams tested and working
- [ ] Ditto app created in Portal
- [ ] MongoDB connector configured in Portal
- [ ] All 8 collections configured with correct ID mappings
- [ ] Connector enabled and status shows "Running"
- [ ] Initial sync triggered
- [ ] Document counts verified (MongoDB == Ditto)
- [ ] Sync lag < 10 seconds
- [ ] Alerts configured for monitoring
- [ ] Test device connected and syncing

---

## Next Steps

After successful connector setup:

1. **Build Flutter Apps**: Start building iOS/Android/Desktop apps using Ditto SDK
2. **Configure Permissions**: Set up Ditto permissions for multi-tenant access
3. **Test Offline Sync**: Verify offline CRUD and conflict resolution
4. **Monitor Performance**: Track sync lag and optimize as needed
5. **Production Readiness**: Review security, monitoring, and backup strategies

---

**Status**: Connector is a managed service - no maintenance required
**Support**: Contact support@ditto.live for connector issues
**Documentation**: https://docs.ditto.live/cloud/mongodb-connector
