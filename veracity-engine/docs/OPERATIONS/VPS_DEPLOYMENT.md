# VPS Deployment Guide

This guide covers deploying Veracity Engine on a VPS (Virtual Private Server).

## System Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB SSD | 50 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Software Requirements

- Docker 24.0+
- Docker Compose v2.0+
- Python 3.9+
- Ollama 0.1+

## Pre-Deployment Checklist

```bash
# Run dependency validation
python3 scripts/validate-deps.py

# Run health checks (to verify baseline)
./scripts/health-check.sh
```

## Deployment Steps

### 1. Clone Repository

```bash
git clone https://github.com/usorama/veracity-engine.git
cd veracity-engine
```

### 2. Configure Environment

```bash
# Copy example environment file
cp infra/.env.example infra/.env

# Generate secure password
NEO4J_PASSWORD=$(openssl rand -base64 32)
echo "NEO4J_PASSWORD=$NEO4J_PASSWORD" >> infra/.env
echo "NEO4J_AUTH=neo4j/$NEO4J_PASSWORD" >> infra/.env

# Set secure permissions
chmod 600 infra/.env
```

### 3. Install Dependencies

```bash
# Python dependencies
pip3 install -r requirements.txt

# Install Ollama models
ollama pull nomic-embed-text
ollama pull llama3.2
```

### 4. Deploy Services

```bash
# Run deployment script
./scripts/deploy-vps.sh

# Or manually:
cd infra
docker compose up -d
```

### 5. Verify Deployment

```bash
# Run health checks
./scripts/health-check.sh

# Check service status
docker compose -f infra/docker-compose.yml ps
```

## Service Endpoints

| Service | Port | URL |
|---------|------|-----|
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | bolt://localhost:7687 |
| Veracity UI | 5173 | http://localhost:5173 |
| NeoDash | 5005 | http://localhost:5005 |
| Health Check | 8080 | http://localhost:8080/health |

## Firewall Configuration

```bash
# UFW (Ubuntu)
ufw allow 22/tcp    # SSH
ufw allow 5173/tcp  # Veracity UI
ufw allow 7474/tcp  # Neo4j Browser (optional - consider SSH tunnel)
ufw allow 7687/tcp  # Neo4j Bolt
ufw enable
```

**Security Note**: Consider NOT exposing Neo4j ports (7474, 7687) publicly. Use SSH tunneling instead:

```bash
# Local machine - create SSH tunnel
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 user@your-vps
```

## Health Checks

### Manual Health Check

```bash
# Full check with console output
./scripts/health-check.sh

# JSON output
./scripts/health-check.sh --json

# Quiet mode (just exit code)
./scripts/health-check.sh --quiet
```

### Automated Health Checks

Add to crontab for monitoring:

```bash
# Check every 5 minutes
*/5 * * * * /path/to/veracity-engine/scripts/health-check.sh --quiet || \
    echo "Health check failed" | mail -s "Veracity Alert" admin@example.com
```

## Updating

### Code Updates

```bash
cd veracity-engine
git pull origin main
pip3 install -r requirements.txt
./scripts/deploy-vps.sh
```

### Docker Updates

```bash
cd infra
docker compose pull
docker compose up -d
```

## Backup & Restore

### Backup Neo4j Data

```bash
# Stop services
docker compose -f infra/docker-compose.yml stop

# Backup data volume
docker run --rm -v neo4j_data:/data -v $(pwd):/backup \
    ubuntu tar cvf /backup/neo4j-backup-$(date +%Y%m%d).tar /data

# Restart services
docker compose -f infra/docker-compose.yml start
```

### Restore Neo4j Data

```bash
# Stop services
docker compose -f infra/docker-compose.yml stop

# Restore data
docker run --rm -v neo4j_data:/data -v $(pwd):/backup \
    ubuntu tar xvf /backup/neo4j-backup-YYYYMMDD.tar -C /

# Restart services
docker compose -f infra/docker-compose.yml start
```

## Troubleshooting

### Service Won't Start

```bash
# Check Docker logs
docker compose -f infra/docker-compose.yml logs

# Check specific service
docker compose -f infra/docker-compose.yml logs neo4j
```

### Neo4j Connection Refused

1. Check container is running: `docker ps`
2. Check credentials in `.env`
3. Check port binding: `netstat -tlnp | grep 7687`

### Ollama Not Responding

1. Check Ollama service: `systemctl status ollama`
2. Restart Ollama: `systemctl restart ollama`
3. Verify models: `ollama list`

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a

# Clean old logs
find /var/log -name "*.log.*" -mtime +7 -delete
```

### High Memory Usage

```bash
# Check memory
free -h

# Restart services to clear memory
docker compose -f infra/docker-compose.yml restart
```

## Scaling Considerations

### Vertical Scaling

Upgrade VPS resources (CPU, RAM) as needed. Recommended thresholds:
- CPU consistently > 80%: Add cores
- RAM consistently > 80%: Add memory
- Disk > 80%: Add storage

### Horizontal Scaling

For multi-node deployment (future):
1. Use Neo4j cluster mode
2. Load balance UI instances
3. Consider Kubernetes deployment

## Monitoring

### Log Files

| Log | Location |
|-----|----------|
| Application | stdout (captured by Docker) |
| Neo4j | `docker logs graphrag_neo4j` |
| UI | `docker logs graphrag_ui` |

### Metrics

Access Prometheus-format metrics:
```bash
curl http://localhost:8080/metrics
```

Key metrics:
- `veracity_build_duration_seconds`
- `veracity_query_count_total`
- `veracity_errors_total`

## Security Best Practices

1. **SSH Access**: Use key-based authentication only
2. **Firewall**: Minimize exposed ports
3. **Secrets**: Use `.env` file with 600 permissions
4. **Updates**: Regular security patches
5. **Backups**: Regular automated backups
6. **Monitoring**: Set up alerts for anomalies

## Support

- Issues: https://github.com/usorama/veracity-engine/issues
- Documentation: See `docs/` directory
