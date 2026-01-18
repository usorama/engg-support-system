---
name: deploy-vps
description: Deploy ESS to VPS with proper verification. Use when deploying changes to production VPS (ess.ping-gadgets.com).
---

# ESS VPS Deployment Skill

Deploy the Engineering Support System to production VPS with comprehensive verification.

## Pre-Deployment Checklist

Before deploying, verify:

1. **Code is committed**: All changes should be committed to git
2. **Tests pass**: Run `bun test` in gateway/ directory
3. **TypeScript compiles**: Run `bun run typecheck` in gateway/
4. **Environment file exists**: `.env.prod` must have all required variables

## Deployment Command

Run the production deployment script:

```bash
cd /Users/umasankr/Projects/engg-support-system
./scripts/deploy-prod.sh
```

## What the Script Does

1. **Validates environment** - checks `.env.prod` exists with required vars
2. **Syncs code to VPS** - git pull or rsync fallback
3. **Builds containers** - Gateway, Chat UI (with API key!), Veracity Engine
4. **Stops old containers** - including Caddy (port conflict prevention)
5. **Starts new containers** - on ess-network
6. **Configures nginx** - unmasks, starts, verifies port 443
7. **Verifies deployment** - E2E tests including API authentication

## Critical Verification Steps

The script automatically verifies:

- [ ] HTTPS endpoint returns 200
- [ ] Health check shows all services OK
- [ ] API authentication works (query returns success)
- [ ] API key is baked into Chat UI bundle
- [ ] nginx owns port 443 (not Caddy)

## Manual Verification (Post-Deploy)

After deployment, manually verify:

```bash
# 1. Health check
curl -s https://ess.ping-gadgets.com/health | jq .

# 2. API query with auth
curl -s -X POST https://ess.ping-gadgets.com/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(grep ESS_API_KEY .env.prod | cut -d= -f2)" \
  -d '{"query": "test", "project": "engg-support-system"}' | jq .status

# 3. Check nginx owns port 443 (not Caddy)
ssh devuser@72.60.204.156 "sudo ss -tlnp | grep ':443'"
# Should show nginx, NOT docker-proxy

# 4. Browser test
# Open https://ess.ping-gadgets.com and submit a query
```

## Troubleshooting

### "API authentication not configured"
- Chat UI was built without `VITE_ESS_API_KEY`
- Fix: Rebuild Chat UI with `--build-arg VITE_ESS_API_KEY="${ESS_API_KEY}"`

### "Unauthorized - check API key"
- API key mismatch between UI bundle and gateway
- Fix: Ensure both use the same key from `.env.prod`

### Port 443 conflict (nginx can't start)
- Another process is using port 443
- Check: `sudo ss -tlnp | grep ':443'`
- Common fix: stop any rogue Docker containers binding to host ports

### nginx is masked
- Previous docker-compose setup masked nginx
- Fix: `sudo systemctl unmask nginx && sudo systemctl start nginx`

## Architecture Decision: nginx Only

**We use nginx (systemd) for TLS termination. Caddy has been completely removed.**

Reasons:
- nginx is managed by systemd (auto-start on boot)
- Let's Encrypt certs via certbot (already configured for VPS)
- VPS already uses nginx for multiple sites (pinglearn, etc.)
- If Docker crashes, nginx can still serve error pages
- Single TLS termination point = simpler architecture

**Caddy Status**: Removed from docker-compose.prod.yml and VPS (Jan 2026)

## Rollback

If deployment fails:

```bash
# 1. Restore previous gateway
ssh devuser@72.60.204.156 "docker stop ess-gateway && docker rm ess-gateway"
# Manually restart with previous image if available

# 2. Restore nginx config
ssh devuser@72.60.204.156 "sudo cp /etc/nginx/sites-available/ess.ping-gadgets.com.bak /etc/nginx/sites-available/ess.ping-gadgets.com && sudo systemctl reload nginx"
```

## Lessons Learned (Encoded in Script)

1. **Always pass VITE_ESS_API_KEY** during Chat UI build (Vite embeds at build time)
2. **Verify nginx owns port 443** - check with `sudo ss -tlnp | grep ':443'`
3. **Unmask nginx** - may be masked from previous Docker setups
4. **E2E API test** - don't just check health, test actual authenticated queries
5. **Single TLS termination** - nginx only, no Docker-based TLS proxies
