# Security Practices

This document describes security practices for Veracity Engine, particularly for VPS deployment.

## Secrets Management

### Environment-Based Secrets

All secrets are loaded from environment variables or `.env` files. **Never commit secrets to version control.**

#### Setting Up Secrets

1. Copy the example environment file:
   ```bash
   cp infra/.env.example infra/.env
   ```

2. Edit `.env` with your secure values:
   ```bash
   # Use a secure password generator
   NEO4J_PASSWORD=$(openssl rand -base64 32)
   echo "NEO4J_PASSWORD=$NEO4J_PASSWORD" >> infra/.env
   ```

3. Set secure file permissions:
   ```bash
   chmod 600 infra/.env
   ```

### Secret Validation

The system validates secrets on startup:

| Check | Severity | Action |
|-------|----------|--------|
| Default password (`password`, `secret`, etc.) | Warning | Logs warning, continues |
| Short password (< 8 chars) | Warning/Error | Logs warning, or raises error in strict mode |
| World-readable `.env` file | Warning | Logs warning about insecure permissions |

#### Strict Mode

Enable strict validation in production:

```python
from core.config import ConfigLoader, validate_secrets

config = ConfigLoader.load()
validate_secrets(config, strict=True)  # Raises ConfigSecurityError on issues
```

### Generating Secure Passwords

```bash
# Generate a 32-character random password
openssl rand -base64 32

# Generate a 16-character alphanumeric password
openssl rand -hex 16

# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

### Environment Variable Naming

| Variable | Description | Required |
|----------|-------------|----------|
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `NEO4J_AUTH` | Neo4j Docker auth (format: `user/pass`) | For Docker |
| `VITE_NEO4J_PASSWORD` | UI Neo4j password | For UI |

New VERACITY_* prefix format is also supported:
- `VERACITY_NEO4J__URI`
- `VERACITY_NEO4J__USER`
- `VERACITY_NEO4J__PASSWORD`

## Version Control Security

### Gitignore Patterns

The following patterns are excluded from version control:

```
.env
.env.local
.env.*.local
*.key
*.pem
*.p12
*.pfx
secrets/
credentials/
```

### Pre-commit Checks

Before committing, verify no secrets are staged:

```bash
# Check for common secret patterns
git diff --cached | grep -iE "(password|secret|api_key|token).*="
```

## VPS Deployment Security

### SSH Access

1. **Disable password authentication**:
   ```bash
   # /etc/ssh/sshd_config
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

2. **Use SSH keys only**:
   ```bash
   ssh-copy-id user@your-vps
   ```

### Firewall Rules

Only expose necessary ports:

```bash
# UFW example
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 7474/tcp   # Neo4j HTTP (optional - for browser access)
ufw allow 7687/tcp   # Neo4j Bolt
ufw allow 5173/tcp   # Veracity UI
ufw enable
```

**Recommended**: Do NOT expose Neo4j HTTP (7474) publicly. Access via SSH tunnel instead.

### File Permissions

| File | Permission | Command |
|------|------------|---------|
| `.env` | 600 | `chmod 600 .env` |
| `*.key` | 600 | `chmod 600 *.key` |
| Scripts | 755 | `chmod 755 scripts/*.sh` |

### Neo4j Security

1. **Change default password** immediately after installation
2. **Enable authentication** (default in Neo4j 5.x)
3. **Use encrypted connections** for production:
   ```yaml
   # docker-compose.yml
   environment:
     - NEO4J_dbms_connector_bolt_tls__level=REQUIRED
   ```

## Runtime Security

### Secret Redaction

Secrets are automatically redacted in:
- Log output
- Error messages
- Configuration dumps

```python
from core.config import redact_config, log_config_summary

config = ConfigLoader.load()
log_config_summary(config)  # Safe - no secrets exposed
redacted = redact_config(config)  # Returns dict with secrets as "****REDACTED****"
```

### Audit Logging

All credential usage is logged (without revealing secrets):

```
2024-01-15 10:30:00 - INFO - Connecting to Neo4j at bolt://localhost:7687 (user: neo4j)
```

## Security Checklist

### Before Deployment

- [ ] `.env` file created with secure passwords
- [ ] `.env` file permissions set to 600
- [ ] No secrets in git repository (`git log -p | grep -i password`)
- [ ] Firewall rules configured
- [ ] SSH key authentication enabled
- [ ] Default passwords changed

### Regular Maintenance

- [ ] Rotate passwords quarterly
- [ ] Update dependencies for security patches
- [ ] Review access logs
- [ ] Check file permissions

## Incident Response

### If Secrets Are Exposed

1. **Immediately rotate** all affected credentials
2. **Check git history** for exposed secrets:
   ```bash
   git log -p --all -S 'password_value'
   ```
3. **Force push** to remove from history (if needed):
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch path/to/file' \
     --prune-empty --tag-name-filter cat -- --all
   ```
4. **Notify** affected parties
5. **Review** access logs for unauthorized access

## Authentication (Future)

Full authentication is deferred per project requirements. Current approach:
- Neo4j username/password authentication
- No API authentication (trusted network assumed)

Future considerations for STORY-XXX:
- JWT token authentication
- API key management
- Role-based access control

## References

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [Neo4j Security Documentation](https://neo4j.com/docs/operations-manual/current/security/)
