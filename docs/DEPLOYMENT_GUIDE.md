# ESS Deployment Guide - VPS Fixes
**Date**: 2026-01-14
**Status**: READY FOR DEPLOYMENT

---

## Executive Summary

All critical bugs have been **fixed in code and committed** to the main branch (commit `2655e52`). The fixes are now ready for deployment to the VPS at ess.ping-gadgets.com.

**What Was Fixed**:
1. ✅ Neo4j password mismatch corrected in .env.prod
2. ✅ Ollama embedding timeout added (30s)
3. ✅ Error logging added to embedding failures
4. ✅ Synthesis provider configuration added to docker-compose
5. ✅ Synthesis model name corrected (glm-4.7 → claude-sonnet-4.5)
6. ✅ Neo4j re-indexed locally with ESS data (1,738 nodes)

**What Still Needs To Be Done On VPS**:
1. Pull latest code (commit `2655e52`)
2. Rebuild and redeploy gateway container
3. Ingest ESS codebase into Qdrant (currently empty)
4. Verify end-to-end functionality

---

## Quick Deployment (Recommended)

Run this ONE command on your local machine to deploy all fixes to VPS:

```bash
ssh devuser@ess.ping-gadgets.com 'bash -s' < /Users/umasankr/Projects/engg-support-system/scripts/quick-fix.sh
```

This will:
- Update .env.prod with correct passwords and model names
- Pull latest code
- Rebuild gateway
- Redeploy containers
- Verify health

**Duration**: ~2 minutes

---

## Full Deployment (Complete Verification)

If you want full deployment with Qdrant ingestion and comprehensive testing:

```bash
# 1. Copy deployment script to VPS
scp /Users/umasankr/Projects/engg-support-system/scripts/vps-deploy-and-verify.sh \
    devuser@ess.ping-gadgets.com:/home/devuser/Projects/engg-support-system/scripts/

# 2. Run deployment script on VPS
ssh devuser@ess.ping-gadgets.com
cd /home/devuser/Projects/engg-support-system
bash scripts/vps-deploy-and-verify.sh
```

**Duration**: ~15 minutes (includes Qdrant ingestion)

---

## Manual Deployment Steps

If you prefer to run commands manually:

### Step 1: Update Configuration Files

```bash
# SSH to VPS
ssh devuser@ess.ping-gadgets.com
cd /home/devuser/Projects/engg-support-system

# Fix Neo4j password
sed -i 's/NEO4J_PASSWORD=testpassword/NEO4J_PASSWORD=password123/' .env.prod

# Fix synthesis model name
sed -i 's/SYNTHESIS_MODEL=glm-4.7/SYNTHESIS_MODEL=claude-sonnet-4.5/' .env.prod
```

### Step 2: Pull Latest Code

```bash
git pull origin main
# Should update to commit 2655e52
```

### Step 3: Rebuild Gateway

```bash
cd gateway
npm install --production
npm run build
cd ..
```

### Step 4: Redeploy Gateway Container

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build ess-gateway

# Wait for healthy status
docker ps | grep ess-gateway
# Should show "healthy" after ~30 seconds
```

### Step 5: Ingest ESS into Qdrant

```bash
cd knowledge-base
npm install
npm run ingest -- --project ess --root-dir /home/devuser/Projects/engg-support-system

# This takes 10-15 minutes
# Watch progress: tail -f logs/ingestion.log
```

### Step 6: Verify Deployment

```bash
# Check health
curl http://localhost:3001/health | jq

# Verify Neo4j data
docker exec ess-neo4j cypher-shell -u neo4j -p password123 \
    "MATCH (n) WHERE n.project = 'ess' RETURN count(n)"
# Should show > 1700 nodes

# Verify Qdrant data
curl http://localhost:6333/collections/ess_knowledge_base | jq '.result.points_count'
# Should show > 0 points

# Test end-to-end query
curl -X POST http://localhost:3001/api/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer 72774e042f90c353b9a6433f70c65b63c5efc7861046428a016e4d91e7b98a6a" \
    -d '{"query":"What is ESS?"}' | jq
# Should return results with status: "success"
```

---

## Verification Checklist

After deployment, verify these conditions are TRUE:

- [ ] Gateway container is healthy: `docker ps | grep ess-gateway`
- [ ] Neo4j password works: `docker exec ess-neo4j cypher-shell -u neo4j -p password123 "RETURN 1"`
- [ ] Neo4j has ESS data: Node count > 1700, sample paths contain "gateway/" or "veracity-engine/"
- [ ] Qdrant has embeddings: `points_count > 0` in collection
- [ ] Health endpoint responds: `/health` returns status "healthy" or "degraded"
- [ ] Query returns results: POST to `/api/query` with "What is ESS?" returns semantic + structural results
- [ ] Synthesis works: Query response includes `answer` field (not just raw results)
- [ ] UI is accessible: https://ess.ping-gadgets.com/ loads and can send queries
- [ ] No authentication errors in logs: `docker logs ess-gateway | grep -i "unauthorized"`

---

## Expected Results

### Successful Deployment

```json
{
  "gateway_health": "healthy",
  "neo4j": {
    "status": "healthy",
    "nodes": 1738,
    "sample_file": "gateway/src/agents/EnggContextAgent.ts"
  },
  "qdrant": {
    "status": "healthy",
    "points": "> 0",
    "collection": "ess_knowledge_base"
  },
  "query_test": {
    "status": "success",
    "semantic_results": "> 0",
    "structural_results": "> 0",
    "answer": "present (synthesis working)"
  }
}
```

### Chat UI Behavior

**Before Fixes**:
- "No matches found" on every query
- "Synthesis unavailable: model 'glm-4.7' not found"
- "Neo4j structural search unavailable"

**After Fixes**:
- Returns semantic results from Qdrant
- Returns structural results from Neo4j
- Synthesis generates answer using zAI/Anthropic API
- No error messages in UI

---

## Rollback Procedure

If deployment fails, rollback to previous state:

```bash
# Stop new gateway
docker stop ess-gateway

# Revert to previous commit
git reset --hard 780ab36

# Rebuild and restart
cd gateway && npm run build && cd ..
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d ess-gateway
```

---

## Troubleshooting

### Gateway Won't Start

Check logs:
```bash
docker logs ess-gateway --tail 100
```

Common issues:
- Missing environment variables: Verify .env.prod has all SYNTHESIS_* vars
- Neo4j auth failure: Verify NEO4J_PASSWORD=password123
- Port conflicts: Check if port 3001 is already in use

### Neo4j Authentication Errors

```bash
# Test connection
docker exec ess-neo4j cypher-shell -u neo4j -p password123 "RETURN 1"

# If fails, check Neo4j container env
docker inspect ess-neo4j | grep NEO4J_AUTH
```

### Qdrant Ingestion Fails

```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Check Ollama is available (needed for embeddings)
curl http://localhost:11434/api/tags

# Verify nomic-embed-text model
docker exec kb-ollama ollama list | grep nomic-embed-text
```

### Query Returns Empty Results

```bash
# Check Qdrant has data
curl http://localhost:6333/collections/ess_knowledge_base | jq '.result.points_count'

# Check Neo4j has data
docker exec ess-neo4j cypher-shell -u neo4j -p password123 \
    "MATCH (n) WHERE n.project = 'ess' RETURN count(n)"

# If either is 0, re-run ingestion/indexing
```

---

## Code Changes Summary

### Files Modified

1. **gateway/src/agents/EnggContextAgent.ts**
   - Added AbortController with 30s timeout to embedding fetch
   - Added error logging for embedding failures
   - Lines 308-347

2. **docker-compose.prod.yml**
   - Added SYNTHESIS_PROVIDER environment variable
   - Added SYNTHESIS_API_URL environment variable
   - Added SYNTHESIS_API_KEY environment variable
   - Added SYNTHESIS_MODEL environment variable
   - Added SYNTHESIS_TIMEOUT environment variable
   - Lines 76-81

3. **.env.prod** (not in git, update manually on VPS)
   - Changed NEO4J_PASSWORD from "testpassword" to "password123"
   - Changed SYNTHESIS_MODEL from "glm-4.7" to "claude-sonnet-4.5"

### New Files

1. **docs/ROOT_CAUSE_ANALYSIS.md**
   - Complete forensic analysis with evidence
   - 7 root causes documented
   - Verification methods provided

2. **scripts/vps-deploy-and-verify.sh**
   - Comprehensive deployment script
   - Includes all steps + verification

3. **scripts/quick-fix.sh**
   - Quick deployment for critical fixes only
   - 2-minute deployment time

---

## Support

If issues persist after deployment:

1. Check deployment log: `~/Projects/engg-support-system/logs/deployment-*.log`
2. Review root cause analysis: `docs/ROOT_CAUSE_ANALYSIS.md`
3. Check gateway logs: `docker logs ess-gateway`
4. Verify all services: `docker ps -a`

---

**Deployment Status**: READY
**Last Updated**: 2026-01-14
**Git Commit**: 2655e52
