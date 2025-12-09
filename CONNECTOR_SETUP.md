# Ditto MongoDB Connector - Setup Guide

This guide walks through deploying and configuring the Ditto MongoDB Connector for the Zava Retail demo application.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Enable MongoDB Change Streams](#enable-mongodb-change-streams)
3. [Deployment Options](#deployment-options)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration](#configuration)
7. [Initial Data Sync](#initial-data-sync)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- ✅ MongoDB Atlas cluster (M10+ recommended for production)
- ✅ MongoDB 4.4+ with Change Streams support
- ✅ Ditto account with app created (https://portal.ditto.live)
- ✅ Docker or Kubernetes cluster for connector deployment

### Environment Variables
Ensure these are set in `.env`:

```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=retail-demo

# Ditto Configuration
DITTO_APP_ID=your_ditto_app_id_here
DITTO_API_KEY=your_ditto_api_key_here
DITTO_CLOUD_ENDPOINT=https://cloud.ditto.live
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

```bash
python scripts/test_change_streams.py
```

Expected output:
```
✓ Change Streams enabled on stores
✓ Change Streams enabled on customers
✓ Change Streams enabled on categories
✓ Change Streams enabled on products
✓ Change Streams enabled on inventory
✓ Change Streams enabled on orders
✓ Change Streams enabled on order_items
```

---

## Deployment Options

The Ditto MongoDB Connector can be deployed in three ways:

1. **Docker** (easiest for development/testing)
2. **Kubernetes** (recommended for production)
3. **Ditto Cloud** (managed service, contact Ditto support)

---

## Docker Deployment

### Step 1: Create Docker Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  ditto-connector:
    image: ditto/mongodb-connector:latest
    container_name: zava-ditto-connector
    restart: unless-stopped

    # Environment variables
    env_file:
      - .env

    # Mount configuration file
    volumes:
      - ./config/ditto-connector.yaml:/config/ditto-connector.yaml:ro

    # Expose metrics and health check ports
    ports:
      - "8080:8080"  # Health check
      - "9090:9090"  # Prometheus metrics

    # Command to run connector with config
    command: [
      "--config", "/config/ditto-connector.yaml"
    ]

    # Resource limits (adjust based on data volume)
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"

    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Step 2: Start the Connector

```bash
# From the project root directory
cd /Users/labeaaa/Developer/ditto/ai-tour-26-zava-diy-dataset-plus-mcp

# Start connector
docker-compose up -d

# View logs
docker-compose logs -f ditto-connector

# Check health
curl http://localhost:8080/health
```

### Step 3: Verify Sync

```bash
# Check connector metrics
curl http://localhost:9090/metrics | grep ditto_sync

# Monitor sync progress
docker-compose logs -f ditto-connector | grep "sync"
```

---

## Kubernetes Deployment

### Step 1: Create Kubernetes Resources

#### ConfigMap for Connector Configuration

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ditto-connector-config
  namespace: ditto
data:
  ditto-connector.yaml: |
    # Copy contents of config/ditto-connector.yaml here
    # Or use --from-file flag below
```

#### Secret for Credentials

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ditto-connector-secrets
  namespace: ditto
type: Opaque
stringData:
  MONGODB_CONNECTION_STRING: "mongodb+srv://username:password@cluster.mongodb.net/"
  MONGODB_DATABASE: "retail-demo"
  DITTO_APP_ID: "your_app_id"
  DITTO_API_KEY: "your_api_key"
  DITTO_CLOUD_ENDPOINT: "https://cloud.ditto.live"
```

#### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ditto-connector
  namespace: ditto
  labels:
    app: ditto-connector
spec:
  replicas: 1  # Only 1 connector instance per database!
  selector:
    matchLabels:
      app: ditto-connector
  template:
    metadata:
      labels:
        app: ditto-connector
    spec:
      containers:
      - name: connector
        image: ditto/mongodb-connector:latest
        imagePullPolicy: Always

        # Environment variables from secret
        envFrom:
        - secretRef:
            name: ditto-connector-secrets

        # Mount config file
        volumeMounts:
        - name: config
          mountPath: /config
          readOnly: true

        # Command
        args:
        - "--config"
        - "/config/ditto-connector.yaml"

        # Ports
        ports:
        - name: health
          containerPort: 8080
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP

        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: health
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health
            port: health
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        # Resource limits
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi

      # Volume for config
      volumes:
      - name: config
        configMap:
          name: ditto-connector-config
```

#### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ditto-connector
  namespace: ditto
  labels:
    app: ditto-connector
spec:
  type: ClusterIP
  ports:
  - name: health
    port: 8080
    targetPort: health
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: metrics
    protocol: TCP
  selector:
    app: ditto-connector
```

#### ServiceMonitor (Prometheus)

```yaml
# k8s/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ditto-connector
  namespace: ditto
  labels:
    app: ditto-connector
spec:
  selector:
    matchLabels:
      app: ditto-connector
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Step 2: Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace ditto

# Create ConfigMap from file
kubectl create configmap ditto-connector-config \
  --from-file=ditto-connector.yaml=config/ditto-connector.yaml \
  -n ditto

# Create Secret
kubectl apply -f k8s/secret.yaml

# Deploy connector
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/servicemonitor.yaml

# Check status
kubectl get pods -n ditto
kubectl logs -f deployment/ditto-connector -n ditto
```

---

## Configuration

### ID Mapping Strategies

The connector configuration defines how MongoDB `_id` maps to Ditto `_id`:

#### 1. Match IDs (1:1)
```yaml
collections:
  - name: "categories"
    idMapping:
      mode: "match"
```
- MongoDB `_id` = Ditto `_id` (identical)

#### 2. Single Field Mapping
```yaml
collections:
  - name: "products"
    idMapping:
      mode: "single"
      field: "product_id"
```
- MongoDB field `product_id` → Ditto `_id`
- Field must be duplicated in document body

#### 3. Multiple Field Mapping (Composite)
```yaml
collections:
  - name: "inventory"
    idMapping:
      mode: "multiple"
      fields:
        - "store_id"
        - "product_id"
```
- MongoDB fields → Ditto composite `_id`
- Example: `{ _id: { store_id: "...", product_id: "..." } }`

### Sync Filters

Limit which documents sync to Ditto using DQL (Ditto Query Language):

```yaml
collections:
  - name: "orders"
    filter: "order_date >= '2023-01-01T00:00:00Z' && deleted == false"
```

**Common Filters**:
- `deleted == false` - Only active records
- `store_id == 'store_123'` - Single store
- `created_at >= '2024-01-01T00:00:00Z'` - Recent data only

---

## Initial Data Sync

Existing MongoDB data doesn't automatically sync until modified. There are two approaches:

### Option 1: Trigger Sync with Touch Script

```bash
python scripts/trigger_initial_sync.py
```

This script updates `last_updated` timestamp on all documents to trigger change streams.

### Option 2: Manual Touch (Small Datasets)

```javascript
// Touch all documents in a collection
db.products.updateMany(
  {},
  { $set: { _ditto_synced: new Date() } }
)
```

### Option 3: Incremental Sync (Large Datasets)

For 200,000+ orders, sync in batches:

```javascript
// Touch 10,000 documents at a time
const batchSize = 10000;
let processed = 0;

while (processed < db.orders.countDocuments()) {
  db.orders.updateMany(
    {},
    { $set: { _ditto_synced: new Date() } },
    { limit: batchSize, skip: processed }
  );
  processed += batchSize;
  sleep(5000);  // 5 second delay between batches
}
```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "ditto": "connected",
  "sync_lag_seconds": 2.5
}
```

### Prometheus Metrics

```bash
curl http://localhost:9090/metrics
```

**Key Metrics**:
- `ditto_sync_operations_total` - Total sync operations
- `ditto_sync_errors_total` - Total sync errors
- `ditto_sync_lag_seconds` - Current sync lag
- `ditto_documents_synced_total` - Total documents synced
- `mongodb_change_stream_events_total` - Change stream events processed

### Grafana Dashboard

Import the included Grafana dashboard:

```bash
# Import dashboard JSON
grafana-cli dashboards import dashboards/ditto-connector.json
```

**Dashboard Panels**:
- Sync rate (documents/second)
- Error rate (%)
- Sync lag (seconds)
- Memory usage
- CPU usage
- Change stream events

### Connector Logs

```bash
# Docker
docker-compose logs -f ditto-connector

# Kubernetes
kubectl logs -f deployment/ditto-connector -n ditto

# Filter for errors only
kubectl logs deployment/ditto-connector -n ditto | grep ERROR
```

---

## Troubleshooting

### Issue 1: Connector Fails to Start

**Symptoms**: Container crashes immediately, no logs

**Solutions**:
1. Check credentials:
   ```bash
   python scripts/check_credentials.py
   python scripts/test_connection.py
   ```

2. Verify environment variables:
   ```bash
   docker-compose config
   ```

3. Check configuration syntax:
   ```bash
   yamllint config/ditto-connector.yaml
   ```

### Issue 2: Change Streams Not Working

**Symptoms**: No documents syncing, connector logs show "no change events"

**Solutions**:
1. Verify change streams enabled:
   ```bash
   python scripts/test_change_streams.py
   ```

2. Check MongoDB version (4.4+ required):
   ```javascript
   db.version()
   ```

3. Verify replica set (change streams require replica sets):
   ```javascript
   rs.status()
   ```

### Issue 3: High Sync Lag

**Symptoms**: `ditto_sync_lag_seconds` > 60

**Solutions**:
1. Increase connector resources:
   ```yaml
   resources:
     limits:
       cpu: '4'
       memory: 4G
   ```

2. Increase batch size:
   ```yaml
   connector:
     batchSize: 5000  # Default: 1000
   ```

3. Add MongoDB indexes (already done if you ran `create_indexes.py`)

4. Check network latency between connector and MongoDB

### Issue 4: Duplicate Documents in Ditto

**Symptoms**: Same document appears multiple times in Ditto

**Solutions**:
1. Verify ID mapping is correct:
   - Check `idMapping` configuration
   - Ensure ID fields are duplicated in document body

2. Check for NULL or missing ID fields:
   ```javascript
   db.products.find({ product_id: { $exists: false } })
   db.products.find({ product_id: null })
   ```

3. Verify unique indexes exist:
   ```javascript
   db.products.getIndexes()
   ```

### Issue 5: Soft Deletes Not Working

**Symptoms**: Deleted documents still appear in Ditto

**Solutions**:
1. Use soft deletes (not hard deletes):
   ```javascript
   // WRONG - hard delete
   db.products.deleteOne({ product_id: "prod_123" })

   // CORRECT - soft delete
   db.products.updateOne(
     { product_id: "prod_123" },
     { $set: { deleted: true, deleted_at: new Date() } }
   )
   ```

2. Add sync filter in connector config:
   ```yaml
   collections:
     - name: "products"
       filter: "deleted == false"
   ```

### Issue 6: Permission Denied Errors

**Symptoms**: Connector logs show "permission denied" or "unauthorized"

**Solutions**:
1. Verify MongoDB user has required permissions:
   - `read` on target database
   - `changeStream` on target database
   - `listCollections` on target database

2. Check Ditto API key has correct permissions:
   - Navigate to Ditto Cloud Portal
   - Verify API key has "Connector" role

3. Test credentials manually:
   ```bash
   python scripts/test_connection.py
   ```

### Issue 7: Vector Search Indexes Missing

**Symptoms**: Product search not working, no similarity results

**Solutions**:

Vector search indexes must be created via MongoDB Atlas UI (not via API):

1. Navigate to MongoDB Atlas → Collections → Search
2. Click "Create Search Index"
3. Select "JSON Editor"
4. Create index for `image_embedding`:
   ```json
   {
     "mappings": {
       "dynamic": false,
       "fields": {
         "image_embedding": {
           "type": "knnVector",
           "dimensions": 512,
           "similarity": "cosine"
         }
       }
     }
   }
   ```
5. Name it `vector_image_search`
6. Repeat for `description_embedding` (1536 dimensions)

---

## Best Practices

### 1. Only Run One Connector Per Database

⚠️ **IMPORTANT**: Only run **one** connector instance per MongoDB database to avoid duplicate syncs and conflicts.

### 2. Monitor Sync Lag

Set up alerts for `ditto_sync_lag_seconds > 60` to catch performance issues early.

### 3. Use Soft Deletes

Always use `deleted: false` flag instead of hard deletes to prevent data loss.

### 4. Duplicate ID Fields

Always duplicate ID fields in document body alongside `_id`:

```json
{
  "_id": { "store_id": "store_123", "product_id": "prod_456" },
  "store_id": "store_123",  // Duplicated
  "product_id": "prod_456"  // Duplicated
}
```

### 5. Test in Staging First

Always test connector configuration in staging environment before production deployment.

### 6. Backup Before Initial Sync

Create MongoDB backup before running initial sync on large datasets.

### 7. Use Filters to Reduce Mobile Sync Data

Configure Ditto permissions to limit what each client syncs:

```javascript
// In Ditto Cloud Portal → Permissions
// Limit store managers to their store's data
WHERE store_id == $currentStoreId
```

---

## Next Steps

1. ✅ Enable Change Streams
2. ✅ Deploy Connector (Docker or Kubernetes)
3. ✅ Run Initial Sync
4. ✅ Verify Sync in Ditto Cloud Portal
5. ✅ Configure Ditto Permissions
6. ✅ Test Mobile App Sync
7. ✅ Set up Monitoring & Alerts

---

## Resources

- **Ditto Documentation**: https://docs.ditto.live/
- **MongoDB Connector Docs**: https://docs.ditto.live/cloud/mongodb-connector
- **Ditto Cloud Portal**: https://portal.ditto.live/
- **MongoDB Atlas**: https://cloud.mongodb.com/
- **Support**: support@ditto.live

---

## Appendix: Sample Queries

### Query Orders with Items (MongoDB)

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

### Query Orders with Items (Ditto)

```swift
// Swift - Ditto SDK
let order = try await ditto
  .store.collection("orders")
  .findById("order_123").exec()

let items = try await ditto
  .store.collection("order_items")
  .find("order_id == 'order_123'").exec()
```

### Vector Similarity Search (MongoDB)

```javascript
db.product_embeddings.aggregate([
  { $vectorSearch: {
      index: "vector_description_search",
      path: "description_embedding",
      queryVector: [...],  // 1536-dim vector
      numCandidates: 100,
      limit: 10
  }},
  { $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "product_id",
      as: "product"
  }},
  { $unwind: "$product" }
])
```

---

**Document Version**: 1.0
**Last Updated**: 2024-12-07
**Status**: Ready for Deployment
