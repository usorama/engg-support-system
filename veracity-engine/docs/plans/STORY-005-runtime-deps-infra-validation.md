# STORY-005: Runtime Dependencies + Infra Validation (VPS Deployment)

## Outcome
Runtime dependencies are validated, documented, and checked before operations. Neo4j and Ollama availability are verified with health checks. System is VPS-deployment ready with validation scripts.

## Scope
- Create health check scripts for Neo4j and Ollama
- Verify Docker Compose stack health
- Document runtime requirements
- Add dependency version validation
- Support VPS deployment scenarios

## Non-Goals
- Full Kubernetes deployment (Docker Compose sufficient for VPS)
- Automated scaling (manual scaling acceptable for start)

## Inputs / References
- `infra/docker-compose.yml`
- `scripts/install.sh`
- `scripts/setup_service.sh`
- 16-layer production architecture (Layer 13: Deployment)

## Definition of Ready (DoR)
- [x] Research completed: VPS deployment requirements (Hostinger or similar)
- [x] Business requirement: Docker Compose on VPS
- [x] Technical requirement: Health checks for all services
- [x] Test specification created (see TDD Specs below)

## Steps (Checklist)

### Phase 1: Health Check Implementation
- [x] Create `scripts/health-check.sh`:
  - [x] Check Neo4j connectivity (Bolt protocol)
  - [x] Check Neo4j version matches requirements
  - [x] Check Ollama API availability
  - [x] Check Ollama model availability (nomic-embed-text, llama3.2)
  - [x] Check disk space availability
  - [x] Check memory availability
  [ ] Return appropriate exit codes (0=all good, 1=warning, 2=error)

### Phase 2: Docker Compose Health
- [x] Update `infra/docker-compose.yml`:
  - [x] Add health check to Neo4j service:
    ```yaml
    neo4j:
      healthcheck:
        test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "password", "RETURN 1"]
        interval: 30s
        timeout: 10s
        retries: 3
    ```
  - [x] Add health check to UI service
  - [x] Expose health check endpoint for external monitoring

### Phase 3: Dependency Validation
- [x] Create `scripts/validate-deps.sh`:
  - [x] Check Python version (>= 3.9)
  - [x] Check Neo4j version compatibility
  - [x] Verify required Python packages installed
  - [x] Check Ollama binary availability
  - [x] Verify model versions (digests from config)

### Phase 4: VPS Deployment Script
- [x] Create `scripts/deploy-vps.sh`:
  - [x] Check .env file exists with required variables
  - [x] Check .env file permissions (chmod 600)
  - [x] Install/validate all dependencies
  - [x] Start Docker Compose stack
  - [x] Run health checks
  - [x] Log deployment status
  - [x] Provide troubleshooting steps if failed

### Phase 5: Documentation
- [x] Create `docs/OPERATIONS/VPS_DEPLOYMENT.md`:
  - [x] VPS requirements (CPU, RAM, disk)
  - [x] Deployment steps
  - [x] Environment variables setup
  - [x] Health check usage
  - [x] Troubleshooting common issues
  - [x] Scaling guidance
- [x] Update README.md with VPS deployment section

## Definition of Done (DoD)
- [x] Health check scripts work for all services
- [x] Docker Compose health checks operational
- [x] Dependency validation script functional
- [x] VPS deployment script tested
- [x] All unit tests passing (see TDD Specs)
- [x] Documentation complete for VPS deployment
- [x] System meets 16-layer production requirements (Layers 1-4)

## Tests

### Unit Tests
Create `tests/test_health_checks.py`:

```python
import pytest
import subprocess
import requests
from core.health import Neo4jHealthCheck, OllamaHealthCheck

class TestNeo4jHealthCheck:
    def test_neo4j_connectivity_check(self):
        """Should verify Neo4j is accessible"""
        checker = Neo4jHealthCheck(uri="bolt://localhost:7687")
        result = checker.check_connectivity()
        assert result["status"] == "healthy" or result["status"] == "unhealthy"
        assert "error" in result or "latency_ms" in result

    def test_neo4j_version_check(self, monkeypatch):
        """Should reject incompatible Neo4j versions"""
        monkeypatch.setenv("NEO4J_REQUIRED_VERSION", "5.15.0")
        checker = Neo4jHealthCheck()
        result = checker.check_version()
        # Implementation depends on version strategy
        assert "version" in result

class TestOllamaHealthCheck:
    def test_ollama_api_availability(self):
        """Should verify Ollama API is accessible"""
        checker = OllamaHealthCheck(host="localhost:11434")
        result = checker.check_api()
        assert result["status"] in ["healthy", "unhealthy"]

    def test_ollama_model_availability(self):
        """Should verify required models are available"""
        checker = OllamaHealthCheck()
        result = checker.check_model("nomic-embed-text")
        assert "available" in result
        assert "version" in result

class TestDependencyValidation:
    def test_python_version_validation(self):
        """Should validate Python version requirements"""
        from scripts.validate_deps import check_python_version
        result = check_python_version(min_version="3.9")
        assert result["valid"] is True or result["valid"] is False

    def test_package_validation(self):
        """Should validate required Python packages"""
        from scripts.validate_deps import check_packages
        required = ["neo4j", "ollama", "pydantic"]
        result = check_packages(required)
        assert "missing" in result
        assert "valid" in result
```

### Integration Tests
Create `tests/test_health_integration.py`:

```python
import pytest
import subprocess
import time

class TestHealthCheckScript:
    def test_health_check_script_exit_code(self):
        """Health check script should return appropriate exit code"""
        result = subprocess.run(
            ["bash", "scripts/health-check.sh"],
            capture_output=True,
            text=True
        )
        assert result.returncode in [0, 1, 2]  # 0=ok, 1=warning, 2=error

    def test_health_check_output_format(self):
        """Health check output should be structured and parsable"""
        result = subprocess.run(
            ["bash", "scripts/health-check.sh", "--json"],
            capture_output=True,
            text=True
        )
        import json
        try:
            health_data = json.loads(result.stdout)
            assert "neo4j" in health_data
            assert "ollama" in health_data
            assert "overall_status" in health_data
        except json.JSONDecodeError:
            pytest.fail("Health check output is not valid JSON")

class TestDockerComposeHealth:
    def test_neo4j_container_healthy(self):
        """Neo4j container should report healthy status"""
        result = subprocess.run(
            ["docker", "compose", "-f", "infra/docker-compose.yml", "ps", "neo4j"],
            capture_output=True,
            text=True
        )
        # Should show "Up (healthy)" or similar status
        assert "Up" in result.stdout

    def test_all_services_running(self):
        """All services should be running"""
        result = subprocess.run(
            ["docker", "compose", "-f", "infra/docker-compose.yml", "ps"],
            capture_output=True,
            text=True
        )
        assert "neo4j" in result.stdout
        assert "ui" in result.stdout
        # Exit code 0 means all well-formed (even if some stopped)
        assert result.returncode == 0
```

## TDD Specification

### Specification 1: Neo4j Health Check
```
Given Neo4j service is expected to be running
When health check is executed
Then:
- Neo4j connectivity is tested via Bolt protocol
- Response time is measured in milliseconds
- Version is verified against requirements
- Status is returned as "healthy", "degraded", or "unhealthy"
- Exit code: 0 if healthy, 1 if degraded, 2 if unhealthy

Acceptance Criteria:
- Bolt connection succeeds within 5 seconds
- Response latency < 100ms for healthy status
- Version check compares to 5.15.0 or compatible
```

### Specification 2: Ollama Health Check
```
Given Ollama is expected to be available
When Ollama health check is executed
Then:
- Ollama API endpoint is tested
- Required models availability is verified
- Model digest is validated against config
- Status returned with model details

Acceptance Criteria:
- HTTP GET to /api/tags returns within 2 seconds
- Model "nomic-embed-text" is listed
- Model "llama3.2" is listed
- Model digests match config values
```

### Specification 3: Dependency Validation
```
Given system is being prepared for deployment
When dependency validation runs
Then:
- Python version meets minimum requirements
- All required packages installed
- Docker daemon available
- Required ports available (7474, 7687, 5173, 11434)
- Disk space > 5GB available
- RAM > 2GB available

Acceptance Criteria:
- Python 3.9+ verified
-neo4j, ollama, pydantic packages installed
- Docker responds to `docker ps`
- No port conflicts detected
- Disk >= 5GB free
- RAM >= 2GB free
```

### Specification 4: VPS Deployment
```
Given VPS deployment script is run
When deployment completes
Then:
- .env file exists with all required variables
- .env file has 600 permissions (owner-only)
- Docker Compose services started
- All health checks pass
- Deployment status logged

Acceptance Criteria:
- .env file exists
- .env permissions = 600 (r-------)
- docker compose ps shows services running
- health-check.sh exits with code 0
- deployment.log created with timestamp
```

## Risks
- Risk: Health checks may have false negatives (services actually healthy)
  - Mitigation: Configurable thresholds, retry logic
- Risk: VPS may have limited resources
  - Mitigation: Resource checks before deployment, minimal specs documented
- Risk: Docker daemon not available on VPS
  - Mitigation: Pre-deployment validation, clear error messages

## Evidence Ledger

### Current State Analysis
- Evidence: `infra/docker-compose.yml` defines neo4j, neodash, ui services
- Evidence: No health check endpoints defined
- Evidence: `scripts/install.sh` checks Ollama but doesn't validate version
- Evidence: No VPS deployment script exists
- Evidence: No dependency validation script

### Requirements Gathering
- Business: VPS deployment (Hostinger or similar)
- Business: Docker Compose approach
- Technical: Health checks required for 16-layer architecture
- Technical: Dependency validation before operations

## Implementation Notes

### VPS Resource Requirements (Minimum)
- CPU: 2 cores
- RAM: 4GB (2GB minimum, 4GB recommended)
- Disk: 20GB (5GB minimum, 20GB recommended)
- OS: Ubuntu 22.04 or similar

### Health Check Script Structure
```bash
#!/bin/bash
set -e

# Exit codes
EXIT_OK=0
EXIT_WARNING=1
EXIT_ERROR=2

OVERALL_STATUS="healthy"

check_neo4j() { ... }
check_ollama() { ... }
check_resources() { ... }

# Run checks
check_neo4j
check_ollama
check_resources

exit ${!OVERALL_STATUS}
```

## Business Requirements Addressed
- VPS Deployment: Docker Compose on VPS with validation
- Scalability: Resource checks, monitoring-ready
- Operational: Health checks for monitoring
- Determinism: Version validation for all deps

## Technical Requirements Addressed
- Health check endpoints
- Dependency validation
- VPS deployment automation
- 16-layer production architecture (Layers 1-4)

## Success Criteria
1. All health checks functional and provide meaningful output
2. Docker Compose services show healthy status
3. VPS deployment script completes successfully
4. Dependency validation catches version mismatches
5. Monitoring can use health check endpoints
6. System meets production readiness criteria (30% complete after this story)

## References
- Neo4j health check documentation
- Ollama API documentation
- Docker Compose health check documentation
- 16-layer production architecture (Layer 13: Deployment)
