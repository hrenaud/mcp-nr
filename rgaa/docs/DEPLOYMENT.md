# DEPLOYMENT.md — mcp-rgaa and greenit-mcp

## Overview

This guide covers deploying, configuring, and managing both the **mcp-rgaa** (RGAA 4.2.1 accessibility auditing) and **greenit-mcp** (environmental impact assessment) services. Both services share an identical stack (Python 3.13 + FastMCP 3.2.4 + Docker) and support two transport modes: **stdio** (for local/testing) and **HTTP** (for production deployment). This document covers Docker Compose deployment, local development, token management, testing, and troubleshooting.

## Project Locations

| Service | Repository | Branch | Tools | Tests | Test Files |
|---------|------------|--------|-------|-------|------------|
| mcp-rgaa | `/Users/renaudheluin/DEV/mcp-rgaa` | main | 10 | 227 | 8 files |
| greenit-mcp | `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit` | main | 9 | 191 | 7 files |

## Environment Variables

All environment variables are shared between mcp-rgaa and greenit-mcp. Configure these for both services in docker-compose.yml or as runtime arguments.

| Variable | Default | Usage | Recommended Value |
|----------|---------|-------|-------------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode (stdio or http) | `http` (production), `stdio` (testing) |
| `MCP_HOST` | `0.0.0.0` | Bind address (HTTP mode only) | `0.0.0.0` (Docker), `127.0.0.1` (local) |
| `MCP_PORT` | `8000` | Server port (HTTP mode only) | `8000` (internal), mapped to 8001/8002 in docker-compose |
| `MCP_BASE_URL` | `http://localhost:8000` (auto-detect) | Public URL behind reverse proxy | `https://mcp.example.com/rgaa` or `/greenit` |
| `MCP_TOKEN_REQUEST_URL` | Empty | URL for token request forms | `https://example.com/tokens/request` |
| `LOG_LEVEL` | `INFO` | Logging verbosity (Python logging) | `DEBUG` (development), `INFO` (production) |
| `PYTHONUNBUFFERED` | `0` | Unbuffered stdout/stderr | `1` (always, for Docker) |

**Notes:**
- Both services use identical environment variable handling
- `MCP_TRANSPORT=http` enables HTTP mode; unset or `stdio` runs in stdio mode
- `MCP_BASE_URL` is used for generating URLs in responses (install scripts, etc.)
- Token authentication is managed via Bearer tokens in Authorization headers

## Docker Compose Deployment (Recommended for Production)

### 1. Prerequisites

- **Docker** and **Docker Compose** (version 1.29+)
- **Python 3.13** (for local development only; not required for Docker deployment)
- **git** (for cloning repositories)
- Ports **8001** and **8002** available (or adjust in docker-compose.yml)

### 2. Clone Both Services

```bash
cd /Users/renaudheluin/DEV

# Clone mcp-rgaa (substitute your repository URL)
git clone https://github.com/<your-username>/mcp-rgaa.git /Users/renaudheluin/DEV/mcp-rgaa

# Clone greenit-mcp (substitute your repository URL)
git clone https://github.com/<your-username>/greenit-mcp.git /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
```

### 3. Create Docker Compose Configuration

Create `docker-compose.yml` in `/Users/renaudheluin/DEV/` with the following configuration:

```yaml
version: '3.9'

services:
  rgaa:
    build:
      context: ./mcp-rgaa
      dockerfile: Dockerfile
    image: rgaa-mcp:latest
    container_name: rgaa-mcp-server
    ports:
      - "8001:8000"
    environment:
      MCP_TRANSPORT: ${MCP_TRANSPORT:-http}
      MCP_HOST: ${MCP_HOST:-0.0.0.0}
      MCP_PORT: ${MCP_PORT:-8000}
      MCP_BASE_URL: ${MCP_BASE_URL:-http://localhost:8001}
      MCP_TOKEN_REQUEST_URL: ${MCP_TOKEN_REQUEST_URL:-}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      PYTHONUNBUFFERED: "1"
    volumes:
      - tokens:/app/tokens
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "files/rgaa_mcp.py", "--health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
    networks:
      - mcp-network
    depends_on:
      - rgaa-init-tokens

  greenit:
    build:
      context: ./mcp-greenit
      dockerfile: Dockerfile
    image: greenit-mcp:latest
    container_name: greenit-mcp-server
    ports:
      - "8002:8000"
    environment:
      MCP_TRANSPORT: ${MCP_TRANSPORT:-http}
      MCP_HOST: ${MCP_HOST:-0.0.0.0}
      MCP_PORT: ${MCP_PORT:-8000}
      MCP_BASE_URL: ${MCP_BASE_URL:-http://localhost:8002}
      MCP_TOKEN_REQUEST_URL: ${MCP_TOKEN_REQUEST_URL:-}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      PYTHONUNBUFFERED: "1"
    volumes:
      - tokens:/app/tokens
    shm_size: '256mb'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "greenit_mcp.py", "--health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
    networks:
      - mcp-network
    depends_on:
      - rgaa-init-tokens

  # Initialize tokens volume (creates tokens.json if missing)
  rgaa-init-tokens:
    build:
      context: ./mcp-rgaa
      dockerfile: Dockerfile
    image: rgaa-mcp:latest
    entrypoint: /bin/sh
    command: -c "mkdir -p /app/tokens && touch /app/tokens/tokens.json && chmod 666 /app/tokens/tokens.json"
    volumes:
      - tokens:/app/tokens
    networks:
      - mcp-network

volumes:
  tokens:
    driver: local

networks:
  mcp-network:
    driver: bridge
```

**Configuration Notes:**
- **rgaa service**: Listens on 8001 (maps to internal 8000)
- **greenit service**: Listens on 8002 (maps to internal 8000)
- **tokens volume**: Named volume shared between both services for token storage
- **healthcheck**: Both services include health checks via `--health` flag
- **restart policy**: `unless-stopped` ensures services restart on failure (except manual stop)
- **shm_size**: Greenit service requires 256MB shared memory for Playwright-based analysis

### 4. Start Services

```bash
cd /Users/renaudheluin/DEV

# Build and start both services in background
docker-compose up -d

# Verify services are running
docker-compose ps
```

Expected output:
```
NAME                        COMMAND                  SERVICE      STATUS        PORTS
greenit-mcp-server          "python greenit_mcp.py"  greenit      Up 1 second   0.0.0.0:8002->8000/tcp
rgaa-mcp-server             "python files/rgaa_mcp.py" rgaa        Up 2 seconds   0.0.0.0:8001->8000/tcp
```

### 5. Verify Service Health

```bash
# Check rgaa service logs
docker-compose logs rgaa

# Check greenit service logs
docker-compose logs greenit

# Test rgaa health endpoint
curl -s http://localhost:8001/health | jq '.'

# Test greenit health endpoint
curl -s http://localhost:8002/health | jq '.'

# Expected output (both should return):
# {"status": "ok", "version": "1.2.0"}
```

### 6. View Running Logs

```bash
# Follow logs from both services
docker-compose logs -f

# Follow logs from rgaa only
docker-compose logs -f rgaa

# Follow logs from greenit only
docker-compose logs -f greenit

# View last 50 lines
docker-compose logs --tail=50 rgaa
```

## Token Management (Bearer Authentication)

Both services use Bearer token authentication for API endpoints. Tokens are stored in a Docker volume (`tokens/tokens.json`) and are shared between services.

### Generate a Token

```bash
# Method 1: Generate token using docker-compose exec
docker-compose exec rgaa python -c "
from files.auth import generate_token
token = generate_token(name='Alice', expires_days=30)
print(f'Generated token: {token}')
"

# Method 2: Generate token from local shell (if Python installed)
cd /Users/renaudheluin/DEV/mcp-rgaa
python3 -c "
from files.auth import generate_token
token = generate_token(name='MyApp', expires_days=90)
print(f'Token: {token}')
"
```

Example output:
```
Generated token: rgaa_tok_eJ1d8q2hK9x5mZ3nL7pQ4r6sT9uV2wX4
```

### List Active Tokens

```bash
# List all active tokens
docker-compose exec rgaa python -c "
from files.auth import list_tokens
tokens = list_tokens()
for token_id, token_data in tokens.items():
    print(f'  {token_id}: {token_data[\"name\"]} (expires: {token_data[\"expires_at\"]})')
"
```

### Verify Token (API call)

```bash
# Set token in variable
TOKEN="rgaa_tok_eJ1d8q2hK9x5mZ3nL7pQ4r6sT9uV2wX4"

# Test token with /guide endpoint (lists all tools)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/guide | jq '.tools | length'

# Expected output: 10 (for rgaa)

# Test without token (should fail with 401)
curl -s http://localhost:8001/guide | jq '.error'
# Expected: "Missing or invalid Authorization header"
```

### Revoke Token

```bash
# Revoke a token by name
docker-compose exec rgaa python -c "
from files.auth import revoke_token
revoke_token('MyApp')
print('Token revoked')
"
```

## Local Development (stdio mode)

For local development without Docker, run services in stdio mode. This mode is suitable for testing, debugging, and local development.

### 1. Install Dependencies

#### mcp-rgaa

```bash
cd /Users/renaudheluin/DEV/mcp-rgaa

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# or manually:
pip install fastmcp httpx beautifulsoup4 lxml pytest
```

#### greenit-mcp

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastmcp httpx pytest playwright
```

### 2. Run Server in stdio Mode

```bash
# Terminal 1: Run rgaa server in stdio mode
cd /Users/renaudheluin/DEV/mcp-rgaa
source venv/bin/activate
python files/rgaa_mcp.py
# Server reads from stdin, writes to stdout
# For interactive testing, see MCP client requirements
```

### 3. Run Server in HTTP Mode (Local)

HTTP mode allows testing via curl without Docker. Useful for local testing.

```bash
# Terminal 1: Start server in HTTP mode
cd /Users/renaudheluin/DEV/mcp-rgaa
source venv/bin/activate
MCP_TRANSPORT=http MCP_PORT=8000 python files/rgaa_mcp.py

# Terminal 2: Test endpoints
curl -s http://localhost:8000/health | jq '.'
curl -s http://localhost:8000/guide | jq '.tools | .[0]'
```

### 4. Token Management (Local)

```bash
cd /Users/renaudheluin/DEV/mcp-rgaa
source venv/bin/activate

# Generate token
python -c "
from files.auth import generate_token
token = generate_token('Local-Dev')
print(f'Token: {token}')
"

# Verify token in running HTTP server
TOKEN="<generated-token>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/guide | jq '.tools | length'
```

## Testing

Both services include comprehensive test suites covering all tools, data loading, and authentication.

### Run All Tests (mcp-rgaa)

```bash
cd /Users/renaudheluin/DEV/mcp-rgaa
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v --tb=short

# Run specific test file
python -m pytest tests/test_tools.py -v

# Run tests with coverage
python -m pytest tests/ --cov=files --cov-report=term-missing
```

Expected output: **227 passing tests**

### Run All Tests (greenit-mcp)

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v --tb=short

# Run specific test file
python -m pytest tests/test_tools.py -v
```

Expected output: **191 passing tests**

### Docker Integration Tests

Test services running in Docker containers:

```bash
# Start services
docker-compose up -d

# Wait for services to initialize
sleep 5

# Run integration tests inside containers
docker-compose exec rgaa python -m pytest tests/ -v --tb=short

docker-compose exec greenit python -m pytest tests/ -v --tb=short

# Check exit codes
echo "RGAA tests: $?"
echo "Greenit tests: $?"

# Stop services
docker-compose down
```

### Health Check Verification

```bash
# Verify health checks are working
docker-compose up -d

# Check health status
docker-compose ps

# Status should show "healthy" after ~10 seconds
# If "unhealthy", check logs: docker-compose logs rgaa

# Manual health check
docker-compose exec rgaa python files/rgaa_mcp.py --health
docker-compose exec greenit python greenit_mcp.py --health
```

## Production Deployment Checklist

Before deploying to production, verify all items:

- [ ] Both services tested locally (all tests passing)
- [ ] Docker images built and tagged with version (`docker-compose build`)
- [ ] Environment variables configured (MCP_BASE_URL, LOG_LEVEL, etc.)
- [ ] Tokens volume configured and secured (readable only by containers)
- [ ] Health check endpoints tested and responding
- [ ] Load balancer or reverse proxy configured (if needed)
- [ ] SSL/TLS certificates configured for HTTPS endpoints
- [ ] Logging configured (stdout captured by Docker logging driver)
- [ ] Backup strategy for tokens volume documented
- [ ] Rollback procedure tested (tag images before release)
- [ ] Monitoring/alerting configured for health checks
- [ ] Rate limiting configured (if needed)
- [ ] Network policies configured (firewall rules, VPC restrictions)

## Troubleshooting

### Service fails to start

**Symptom:** Service exits immediately or stays in "starting" state

```bash
# Check logs for errors
docker-compose logs rgaa

# Rebuild container (clears build cache)
docker-compose build --no-cache rgaa

# Start with verbose logging
LOG_LEVEL=DEBUG docker-compose up rgaa
```

**Common causes:**
- Port already in use: `lsof -i :8001` to check; kill or change port in docker-compose.yml
- Python dependency missing: Check `pip install` in build log
- Volume permission issue: `chmod 777 ./tokens` in host directory

### Token endpoints return 401 Unauthorized

**Symptom:** API calls fail with "Missing or invalid Authorization header"

```bash
# Verify Bearer token in request
TOKEN="your-token-here"
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8001/guide

# Check token validity
docker-compose exec rgaa python -c "
from files.auth import verify_token
print(verify_token('$TOKEN'))
"

# Generate new token if expired
docker-compose exec rgaa python -c "
from files.auth import generate_token
print(generate_token('NewToken'))
"
```

**Common causes:**
- Token not provided or malformed: Token must be in header, not query param
- Token expired: Regenerate with `generate_token()`
- Token revoked: Check with `list_tokens()`

### Health endpoint returns error

**Symptom:** Health check failing, service marked "unhealthy"

```bash
# Test health endpoint directly
docker-compose exec rgaa python files/rgaa_mcp.py --health

# Check service logs (errors appear here)
docker-compose logs rgaa | tail -50

# Wait for full startup (health check has start_period of 10s)
sleep 15
docker-compose ps
```

**Common causes:**
- Service still initializing: Wait 10-15 seconds after docker-compose up
- Port not exposed internally: Check Dockerfile EXPOSE directive
- Health check script missing: Verify --health flag exists in entrypoint

### /guide endpoint returns empty tools

**Symptom:** Tool count is 0 instead of 10 (rgaa) or 9 (greenit)

```bash
# Check if server is running
docker-compose ps

# Test /guide endpoint
curl -s http://localhost:8001/guide | jq '.tools | length'

# Check server logs for errors
docker-compose logs rgaa | grep -i error

# Restart service
docker-compose restart rgaa

# If still broken, rebuild
docker-compose build --no-cache rgaa
docker-compose up -d rgaa
```

**Common causes:**
- Server crashed during initialization: Check logs for exceptions
- Data file not loaded: Verify rgaa_cache.json exists in image
- MCP version mismatch: Ensure fastmcp==3.2.4 in requirements

### Port conflicts

**Symptom:** `Error response from daemon: Bind for 0.0.0.0:8001 failed`

```bash
# Check which process is using port
lsof -i :8001

# Option 1: Kill process
kill -9 <PID>

# Option 2: Change port in docker-compose.yml
# Change "8001:8000" to "8003:8000"
# Then restart
docker-compose up -d
```

### Tests failing in Docker

**Symptom:** Tests pass locally but fail in container

```bash
# Run tests with verbose output
docker-compose exec rgaa python -m pytest tests/ -vv --tb=long

# Check Python version
docker-compose exec rgaa python --version
# Should output: Python 3.13.x

# Check installed packages
docker-compose exec rgaa pip list

# Rebuild container to ensure clean state
docker-compose build --no-cache rgaa
docker-compose exec rgaa python -m pytest tests/test_tools.py::TestRGAATools -v
```

**Common causes:**
- Dependencies not installed: Check Dockerfile pip install section
- Mount path issues: Verify VOLUME and volumes in docker-compose.yml
- Python path issues: Ensure PYTHONPATH not overridden

### Greenit service slow or hanging

**Symptom:** Greenit API calls timeout, logs show "playwright" messages

```bash
# Check logs for Playwright-specific errors
docker-compose logs greenit | grep -i playwright

# Increase shm_size in docker-compose.yml (browser memory)
# Change shm_size: '256mb' to shm_size: '512mb'

# Restart with more resources
docker-compose up -d greenit

# Check if Playwright browser is running
docker-compose exec greenit pgrep -l playwright || echo "Not found"
```

**Common causes:**
- Browser resource limit: Increase shm_size in docker-compose.yml
- Browser initialization timeout: Check greenit logs for timeout messages
- Disk space: Verify host has space for browser cache

## Quick Reference

### Common Commands

| Task | Command |
|------|---------|
| Start both services | `docker-compose up -d` |
| Stop services | `docker-compose down` |
| Restart services | `docker-compose restart` |
| View logs (all) | `docker-compose logs -f` |
| View logs (rgaa only) | `docker-compose logs -f rgaa` |
| Health check | `curl http://localhost:8001/health` |
| List tools | `curl http://localhost:8001/guide \| jq '.tools'` |
| Run tests | `docker-compose exec rgaa pytest tests/ -v` |
| Generate token | `docker-compose exec rgaa python -c "from files.auth import generate_token; print(generate_token('Name'))"` |
| Rebuild image | `docker-compose build --no-cache rgaa` |
| Remove containers | `docker-compose rm -f` |
| Inspect container | `docker-compose exec rgaa /bin/sh` |

### Useful curl Examples

```bash
# Test both services are running
curl -s http://localhost:8001/health && echo "RGAA OK"
curl -s http://localhost:8002/health && echo "GreenIT OK"

# Count tools in each service
echo "RGAA tools: $(curl -s http://localhost:8001/guide | jq '.tools | length')"
echo "GreenIT tools: $(curl -s http://localhost:8002/guide | jq '.tools | length')"

# Call a tool (requires valid token)
TOKEN="your-token"
curl -X POST http://localhost:8001/tools/rgaa_lister_criteres \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"theme": 1}'
```

## Additional Resources

- **RGAA 4.2.1 Official**: https://www.numerique.gouv.fr/publications/rgaa-accessibilite/
- **GreenIT 4**: https://www.greenit.fr/
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **Docker Compose Reference**: https://docs.docker.com/compose/
- **MCP Specification**: https://modelcontextprotocol.io/
