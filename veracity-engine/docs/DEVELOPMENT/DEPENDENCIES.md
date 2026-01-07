# Dependency Management

This document describes how Veracity Engine manages Python and Docker dependencies.

## Python Dependencies

### Production Dependencies (requirements.txt)

```
neo4j==5.28.2
ollama==0.6.1
pydantic==2.12.5
pydantic-settings==2.11.0
PyYAML==6.0.3
python-dotenv==1.0.1
pytest==8.4.2
```

### Development Dependencies (requirements-dev.txt)

```
-r requirements.txt

pytest==8.4.2
pytest-cov==6.2.1
pytest-asyncio==1.2.0
black==25.1.0
isort==6.0.1
flake8==7.2.0
mypy==1.16.0
types-PyYAML==6.0.12.20250516
```

## Docker Dependencies

### Neo4j

| Field | Value |
|-------|-------|
| Image | `neo4j` |
| Version | `5.15.0` |
| Digest | `sha256:d9e2fb1ba398536e50d22ebc3d5d585baa086c1c0cf8e5b96bdc9e11e87e002a` |

### NeoDash

| Field | Value |
|-------|-------|
| Image | `neo4jlabs/neodash` |
| Version | `latest` |

## Updating Dependencies

### Python Packages

1. Update version in `requirements.txt`:
   ```
   neo4j==5.29.0  # New version
   ```

2. Install and test:
   ```bash
   pip install -r requirements.txt
   pytest tests/ -v
   ```

3. Verify with model verification script:
   ```bash
   python3 scripts/verify_models.py
   ```

4. Commit with version change note:
   ```bash
   git commit -m "deps: update neo4j to 5.29.0"
   ```

### Docker Images

1. Pull new image:
   ```bash
   docker pull neo4j:5.16.0
   ```

2. Get new digest:
   ```bash
   docker inspect neo4j:5.16.0 --format='{{index .RepoDigests 0}}'
   ```

3. Update `infra/docker-compose.yml`:
   ```yaml
   neo4j:
     image: neo4j@sha256:NEW_DIGEST_HERE
   ```

4. Test:
   ```bash
   cd infra && docker compose up -d
   docker compose logs neo4j
   ```

## Pinning Strategy

### Why Pin Versions?

1. **Reproducibility**: Same dependencies = same behavior
2. **Security**: Known versions can be audited
3. **Stability**: No surprise breaking changes
4. **Debugging**: Easier to reproduce issues

### What to Pin

| Type | Pin Strategy |
|------|--------------|
| Python packages | Exact version (`==`) |
| Docker images | SHA256 digest |
| Ollama models | Version + digest in config |

### What NOT to Pin

- Development tools (can use `>=`)
- Optional dependencies
- Build-time only tools

## Security Updates

### Checking for Vulnerabilities

```bash
# Python packages
pip-audit

# Docker images
docker scout cves neo4j:5.15.0
```

### Security Update Process

1. Identify vulnerable package/version
2. Find patched version
3. Update pinned version
4. Run full test suite
5. Update documentation
6. Create PR with security note

## Version Matrix

| Component | Current | Min Supported | Max Tested |
|-----------|---------|---------------|------------|
| Python | 3.9.6 | 3.9 | 3.12 |
| Neo4j | 5.15.0 | 5.15.0 | 5.28.0 |
| Ollama | 0.6.1 | 0.1.0 | 0.6.1 |
| Pydantic | 2.12.5 | 2.0.0 | 2.12.5 |

## Troubleshooting

### Dependency Conflicts

```
ERROR: Cannot install package-a==1.0 and package-b==2.0 because...
```

Solution:
1. Check `pip show <package>` for dependencies
2. Find compatible versions
3. Update requirements.txt with resolved versions

### Missing Dependencies

```
ModuleNotFoundError: No module named 'xyz'
```

Solution:
```bash
pip install -r requirements.txt
```

### Version Mismatch Warnings

```
[WARN] neo4j: expected 5.28.2, got 5.29.0
```

This is informational. Update requirements.txt if intentional:
```
neo4j==5.29.0
```
