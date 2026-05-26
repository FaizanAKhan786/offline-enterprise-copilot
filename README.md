<p align="center">
  <img src="docs/architecture/logo.svg" alt="OECA Logo" width="120" />
</p>

<h1 align="center">Offline Enterprise AI Copilot</h1>

<p align="center">
  <strong>A fully air-gapped, production-grade AI assistant platform with zero external API dependencies.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#api-reference">API Reference</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/next.js-15-black?logo=next.js" />
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker" />
  <img src="https://img.shields.io/badge/k8s-ready-326CE5?logo=kubernetes" />
  <img src="https://img.shields.io/badge/offline-100%25-orange" />
</p>

---

## Why This Exists

Enterprise environments — defense, healthcare, finance, government — often operate in **air-gapped networks** where cloud AI APIs are not an option. This platform delivers the full power of modern AI assistants using only local, open-source models and infrastructure.

No data leaves your network. Ever.

---

## Features

### Core AI Capabilities

| Capability | Implementation | Details |
|---|---|---|
| **Local LLM Inference** | Ollama / vLLM | Llama 3, Mistral, Qwen with dynamic switching, GGUF quantization, GPU+CPU |
| **Enterprise RAG** | Qdrant + BM25 | Hybrid dense/sparse retrieval, reranking, citation-aware responses |
| **Agentic Workflows** | LangGraph | Research, Summarization, Verification, Translation, Reporting agents |
| **Document Processing** | Tesseract + PyMuPDF | PDF, DOCX, TXT, images with OCR extraction |
| **Voice AI** | Whisper | Speech-to-text, real-time microphone input |
| **Multilingual** | MarianMT | English, Arabic, Hindi — translation + multilingual retrieval |

### Enterprise Features

- **JWT Authentication** with role-based access control (Admin, Analyst, Viewer)
- **Audit logging** — every query, document access, and agent action is traced
- **Semantic caching** via Redis — avoid redundant inference
- **Session memory** — persistent conversation history per user
- **Rate limiting** — configurable per-role API throttling
- **Secure document storage** — encrypted at rest with access controls
- **WebSocket streaming** — real-time token-by-token responses
- **Async task queue** — background document processing with Celery/Redis

### Observability

- Prometheus metrics (latency, throughput, model utilization, queue depth)
- Grafana dashboards (pre-configured JSON provisioning)
- MLflow experiment tracking (model benchmarks, RAG evaluation)
- Structured JSON logging with correlation IDs
- Health check endpoints with dependency status

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX GATEWAY                        │
│                    (TLS · Rate Limiting)                     │
├────────────────────────┬────────────────────────────────────┤
│                        │                                    │
│   ┌────────────────┐   │   ┌──────────────────────────┐     │
│   │  Next.js 15    │   │   │     FastAPI Backend       │     │
│   │  Frontend      │◄──┼──►│                          │     │
│   │                │   │   │  ┌─────────┐ ┌────────┐  │     │
│   │  • Chat UI     │   │   │  │ Auth    │ │ RAG    │  │     │
│   │  • Doc Upload  │   │   │  │ Service │ │ Engine │  │     │
│   │  • Workflows   │   │   │  └─────────┘ └────────┘  │     │
│   │  • Analytics   │   │   │  ┌─────────┐ ┌────────┐  │     │
│   └────────────────┘   │   │  │ Agent   │ │ Voice  │  │     │
│                        │   │  │ Engine  │ │ Engine │  │     │
│                        │   │  └─────────┘ └────────┘  │     │
│                        │   └──────────┬───────────────┘     │
│                        │              │                     │
│   ┌────────────────────┼──────────────┼──────────────────┐  │
│   │              Infrastructure Layer                    │  │
│   │  ┌──────┐  ┌──────┐  ┌───────┐  ┌────────────────┐  │  │
│   │  │Qdrant│  │Postgres│ │ Redis │  │ Ollama / vLLM  │  │  │
│   │  └──────┘  └──────┘  └───────┘  └────────────────┘  │  │
│   └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Prometheus · Grafana · MLflow · Structured Logging         │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- NVIDIA GPU (recommended) or CPU-only mode
- 16GB+ RAM (32GB recommended)
- 50GB+ disk space for models

### 1. Clone & Configure

```bash
git clone https://github.com/yourname/offline-enterprise-copilot.git
cd offline-enterprise-copilot
cp .env.example .env
# Edit .env with your configuration
```

### 2. Launch with Docker Compose

```bash
# GPU mode (requires nvidia-docker)
docker compose -f infra/docker/docker-compose.yml --profile gpu up -d

# CPU-only mode
docker compose -f infra/docker/docker-compose.yml --profile cpu up -d
```

### 3. Pull Models

```bash
# Pull default models into Ollama
docker exec ollama ollama pull llama3:8b
docker exec ollama ollama pull mistral:7b
docker exec ollama ollama pull nomic-embed-text
```

### 4. Access

| Service | URL |
|---|---|
| **Web UI** | `http://localhost:3000` |
| **API** | `http://localhost:8000/docs` |
| **Grafana** | `http://localhost:3001` |
| **Prometheus** | `http://localhost:9090` |
| **MLflow** | `http://localhost:5001` |

Default credentials: `admin` / `changeme-in-production`

---

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

Full OpenAPI documentation is available at `/docs` when the backend is running. Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat/completions` | Chat with streaming support |
| `POST` | `/api/v1/documents/upload` | Upload documents for RAG |
| `POST` | `/api/v1/agents/execute` | Execute agentic workflows |
| `POST` | `/api/v1/voice/transcribe` | Speech-to-text |
| `GET`  | `/api/v1/models` | List available models |
| `POST` | `/api/v1/auth/login` | Authenticate |
| `GET`  | `/api/v1/health` | System health check |

See [docs/api/](docs/api/) for full documentation.

---

## Deployment

### Docker Compose (Recommended for Single Node)

See [infra/docker/](infra/docker/) for production-ready compose files.

### Kubernetes (Multi-Node / HA)

```bash
kubectl apply -k infra/k8s/
```

See [infra/k8s/](infra/k8s/) for Helm-compatible manifests.

---

## Configuration

All configuration is via environment variables. See [`.env.example`](.env.example) for the full list.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama server URL |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant vector DB URL |
| `POSTGRES_DSN` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL |
| `JWT_SECRET` | (required) | JWT signing secret |
| `DEFAULT_MODEL` | `llama3:8b` | Default inference model |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `ENABLE_GPU` | `true` | Enable GPU inference |

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built for environments where the cloud isn't an option.
</p>
