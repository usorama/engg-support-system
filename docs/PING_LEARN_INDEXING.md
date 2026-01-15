# Indexing ping-learn-pwa into ESS (VPS Deployment)

**Date**: 2026-01-15
**VPS**: ess.ping-gadgets.com (72.60.204.156)
**Target**: ping-learn-pwa codebase

---

## Architecture Understanding

**VPS Network Topology**:
```
Internet → HTTPS (443) → Gateway (port 3001) → Docker Network
                                                 ├─ ess-neo4j:7687
                                                 ├─ ess-qdrant:6333
                                                 └─ ess-redis:6379
```

**Key Constraint**: Neo4j and Qdrant are NOT exposed to public internet. They're only accessible:
1. Within the Docker network (service names: `ess-neo4j`, `ess-qdrant`)
2. Via SSH to the VPS host

**Implication**: Indexing must run **from inside the VPS**, not from local machine.

---

## Step 1: Prepare VPS Environment

### 1.1 SSH to VPS

```bash
ssh root@72.60.204.156
```

### 1.2 Ensure ping-learn-pwa Code Exists on VPS

**Option A**: If already deployed
```bash
cd /home/devuser/Projects/ping-learn-pwa
git pull origin main
```

**Option B**: If not yet deployed
```bash
cd /home/devuser/Projects
git clone <ping-learn-pwa-repo-url> ping-learn-pwa
# or rsync from local:
# rsync -avz --exclude node_modules ~/Projects/ping-learn-pwa/ root@72.60.204.156:/home/devuser/Projects/ping-learn-pwa/
```

### 1.3 Install Python Dependencies (if needed)

```bash
cd /home/devuser/Projects/engg-support-system/veracity-engine
pip3 install neo4j ollama pyyaml
```

---

## Step 2: Initial Indexing

### 2.1 Index to Neo4j

Run from VPS, pointing to Docker network service names:

```bash
cd /home/devuser/Projects/engg-support-system/veracity-engine

NEO4J_URI="bolt://ess-neo4j:7687" \
NEO4J_USER="neo4j" \
NEO4J_PASSWORD="password123" \
python3 core/build_graph.py \
  --project-name ping-learn-pwa \
  --root-dir /home/devuser/Projects/ping-learn-pwa \
  --target-dirs app/src app/prisma docs
```

**What this does**:
- Parses TypeScript, JavaScript, Prisma files
- Creates graph nodes: Files, Functions, Classes, Components
- Generates embeddings via Ollama (or falls back)
- Stores in Neo4j with project label: `ping-learn-pwa`

**Expected Output**:
```
Indexing project: ping-learn-pwa
Root: /home/devuser/Projects/ping-learn-pwa
Target dirs: app/src, app/prisma, docs

Processing app/src...
  [  0%] Scanning files...
  [ 25%] Parsing TypeScript AST...
  [ 50%] Generating embeddings...
  [ 75%] Creating graph nodes...
  [100%] Complete!

Summary:
  Files: 530
  Functions: ~1,200
  Classes: ~180
  Nodes created: ~2,000
  Time: ~5-10 minutes
```

### 2.2 Sync Embeddings to Qdrant

```bash
cd /home/devuser/Projects/engg-support-system

NEO4J_URI="bolt://ess-neo4j:7687" \
NEO4J_USER="neo4j" \
NEO4J_PASSWORD="password123" \
QDRANT_URL="http://ess-qdrant:6333" \
PROJECT_NAME="ping-learn-pwa" \
python3 scripts/sync-neo4j-to-qdrant.py
```

**Expected Output**:
```
Syncing project 'ping-learn-pwa' from Neo4j to Qdrant...
Neo4j: bolt://ess-neo4j:7687
Qdrant: http://ess-qdrant:6333
Collection: ess_ping_learn_pwa

Found 2,000 nodes with valid embeddings
  Upserted batch 1: 100 points
  Upserted batch 2: 100 points
  ...
  Upserted batch 20: 100 points

✅ Sync complete!
   Collection: ess_ping_learn_pwa
   Points: 2,000
   Vectors: 2,000
```

---

## Step 3: Verification

### 3.1 Check Neo4j Node Count

```bash
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://ess-neo4j:7687', auth=('neo4j', 'password123'))
with driver.session() as session:
    result = session.run('MATCH (n {project: \"ping-learn-pwa\"}) RETURN count(n) as count')
    print(f'Neo4j nodes: {result.single()[\"count\"]}')
driver.close()
"
```

**Expected**: `Neo4j nodes: ~2000`

### 3.2 Check Qdrant Point Count

```bash
curl http://ess-qdrant:6333/collections/ess_ping_learn_pwa | jq '.result.points_count'
```

**Expected**: `2000` (or similar number matching Neo4j)

### 3.3 Test Query via Gateway (from outside VPS)

From your local machine:

```bash
curl -X POST https://ess.ping-gadgets.com/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 72774e042f90c353b9a6433f70c65b63c5efc7861046428a016e4d91e7b98a6a" \
  -d '{
    "project": "ping-learn-pwa",
    "query": "What are the main components of the ping-learn application?",
    "mode": "hybrid"
  }'
```

**Expected**: JSON response with:
- `status: "success"`
- `neo4jQueried: true`
- `qdrantQueried: true` (now that Qdrant is populated)
- `answer`: Synthesized response about ping-learn components

---

## Step 4: Continuous Sync Setup

### Option A: Git Webhook (Recommended for VPS Deployments)

**Not yet implemented in ESS gateway**. Would require:
1. Adding webhook endpoint to gateway
2. GitHub webhook configuration
3. Auto-pull + re-index on push

**Status**: 🚧 Planned but not built

### Option B: Scheduled Cron Job on VPS

```bash
# On VPS, add to crontab
crontab -e

# Add line (re-index every hour):
0 * * * * cd /home/devuser/Projects/engg-support-system/veracity-engine && NEO4J_URI="bolt://ess-neo4j:7687" NEO4J_USER="neo4j" NEO4J_PASSWORD="password123" python3 core/build_graph.py --project-name ping-learn-pwa --root-dir /home/devuser/Projects/ping-learn-pwa --target-dirs app/src app/prisma docs && NEO4J_URI="bolt://ess-neo4j:7687" QDRANT_URL="http://ess-qdrant:6333" PROJECT_NAME="ping-learn-pwa" python3 /home/devuser/Projects/engg-support-system/scripts/sync-neo4j-to-qdrant.py
```

### Option C: Manual Trigger Script

Create `/home/devuser/bin/reindex-ping-learn.sh`:

```bash
#!/bin/bash
set -e

echo "🔄 Re-indexing ping-learn-pwa..."

cd /home/devuser/Projects/ping-learn-pwa
git pull origin main

cd /home/devuser/Projects/engg-support-system/veracity-engine

NEO4J_URI="bolt://ess-neo4j:7687" \
NEO4J_USER="neo4j" \
NEO4J_PASSWORD="password123" \
python3 core/build_graph.py \
  --project-name ping-learn-pwa \
  --root-dir /home/devuser/Projects/ping-learn-pwa \
  --target-dirs app/src app/prisma docs

NEO4J_URI="bolt://ess-neo4j:7687" \
NEO4J_USER="neo4j" \
NEO4J_PASSWORD="password123" \
QDRANT_URL="http://ess-qdrant:6333" \
PROJECT_NAME="ping-learn-pwa" \
python3 /home/devuser/Projects/engg-support-system/scripts/sync-neo4j-to-qdrant.py

echo "✅ Re-indexing complete!"
```

```bash
chmod +x /home/devuser/bin/reindex-ping-learn.sh

# Run manually whenever needed:
/home/devuser/bin/reindex-ping-learn.sh
```

### Option D: Local Git Hook → SSH Trigger

On your local machine (ping-learn-pwa), create `.git/hooks/post-commit`:

```bash
#!/bin/bash
# Trigger VPS re-indexing after every local commit

echo "📤 Pushing to origin..."
git push origin main

echo "🔄 Triggering VPS re-indexing..."
ssh root@72.60.204.156 "/home/devuser/bin/reindex-ping-learn.sh"

echo "✅ VPS sync triggered!"
```

```bash
chmod +x ~/Projects/ping-learn-pwa/.git/hooks/post-commit
```

---

## Step 5: Production Readiness Analysis

Once indexed, query ESS to identify gaps:

```bash
curl -X POST https://ess.ping-gadgets.com/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 72774e042f90c353b9a6433f70c65b63c5efc7861046428a016e4d91e7b98a6a" \
  -d '{
    "project": "ping-learn-pwa",
    "query": "What features or components are incomplete or need work for production deployment? Identify any TODOs, unfinished functions, or missing integrations.",
    "mode": "hybrid"
  }'
```

---

## Troubleshooting

### Issue: "Connection refused to ess-neo4j"

**Cause**: Running from outside Docker network

**Solution**: Commands must run from VPS, using service names (`ess-neo4j`, not `localhost`)

### Issue: "No embeddings generated"

**Cause**: Ollama service not running or model not loaded

**Check**:
```bash
docker ps | grep ollama
docker exec kb-ollama ollama list
```

**Solution**: Falls back to OpenAI if configured, or synthesis uses Claude API

### Issue: "Qdrant sync found 0 embeddings"

**Cause**: Neo4j nodes don't have embeddings

**Check**:
```bash
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://ess-neo4j:7687', auth=('neo4j', 'password123'))
with driver.session() as session:
    result = session.run('MATCH (n {project: \"ping-learn-pwa\"}) WHERE n.embedding IS NOT NULL RETURN count(n)')
    print(f'Nodes with embeddings: {result.single()[0]}')
driver.close()
"
```

**Solution**: Re-run build_graph.py with Ollama functional

---

## Summary

**What works**:
- ✅ Index codebase from VPS
- ✅ Sync embeddings to Qdrant
- ✅ Query via HTTPS gateway from anywhere
- ✅ Hybrid search (Neo4j + Qdrant)

**What's missing**:
- ❌ Automatic git webhook integration
- ❌ Client-side indexing (must run on VPS)
- ⚠️ Continuous sync requires manual setup (cron or git hook)

**Recommended Workflow**:
1. Develop locally in ping-learn-pwa
2. Commit and push to GitHub
3. SSH to VPS and run `/home/devuser/bin/reindex-ping-learn.sh`
4. Query ESS via gateway from anywhere

---

**Created**: 2026-01-15
**VPS**: ess.ping-gadgets.com
**Status**: Ready for execution
