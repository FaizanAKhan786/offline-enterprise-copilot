#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Pre-flight checks ────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || error "Docker is required but not installed."
command -v docker compose >/dev/null 2>&1 || error "Docker Compose V2 is required."

info "Offline Enterprise AI Copilot — Setup"
echo ""

# ── Environment file ─────────────────────────────────────────────
if [ ! -f "$ROOT_DIR/.env" ]; then
    info "Creating .env from template..."
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    warn "Edit .env to set SECRET_KEY and other values before production use."
fi

# ── Create data directories ──────────────────────────────────────
info "Creating data directories..."
mkdir -p "$ROOT_DIR/data/postgres"
mkdir -p "$ROOT_DIR/data/redis"
mkdir -p "$ROOT_DIR/data/qdrant"
mkdir -p "$ROOT_DIR/data/ollama"
mkdir -p "$ROOT_DIR/data/uploads"
mkdir -p "$ROOT_DIR/data/grafana"

# ── Build and start services ────────────────────────────────────
info "Building containers..."
docker compose -f "$ROOT_DIR/infra/docker/docker-compose.yml" build

info "Starting services..."
docker compose -f "$ROOT_DIR/infra/docker/docker-compose.yml" up -d

# ── Wait for Ollama and pull default model ──────────────────────
info "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

info "Pulling default model (llama3:8b). This may take a while..."
docker compose -f "$ROOT_DIR/infra/docker/docker-compose.yml" exec -T ollama ollama pull llama3:8b || warn "Model pull failed — pull manually with: docker exec ollama ollama pull llama3:8b"

# ── Health check ─────────────────────────────────────────────────
info "Running health checks..."
sleep 5

BACKEND_OK=false
for i in $(seq 1 10); do
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        BACKEND_OK=true
        break
    fi
    sleep 2
done

if $BACKEND_OK; then
    info "Backend is healthy ✓"
else
    warn "Backend health check failed — check logs with: docker compose logs backend"
fi

echo ""
info "Setup complete!"
echo ""
echo "  Frontend:    http://localhost:3000"
echo "  Backend API: http://localhost:8000/docs"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3001  (admin/admin)"
echo ""
echo "  Default admin:  admin@copilot.local / changeme"
echo ""
