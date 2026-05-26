# Contributing to Offline Enterprise AI Copilot

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- NVIDIA GPU (optional, for accelerated inference)
- 16 GB RAM minimum

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/offline-enterprise-copilot.git
cd offline-enterprise-copilot

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Running with Docker

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

## Code Standards

### Python (Backend)

- Follow PEP 8 with a 100-character line limit
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Use `async`/`await` for all I/O operations
- Run `ruff check` and `ruff format` before committing

### TypeScript (Frontend)

- Use strict TypeScript (no `any` types)
- Follow the existing component patterns
- Use named exports for components
- Run `npm run lint` before committing

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Write clear, descriptive commit messages
3. Add tests for new functionality
4. Update documentation if you change APIs or configuration
5. Ensure all CI checks pass
6. Request review from at least one maintainer

## Issue Reporting

When reporting bugs, please include:

- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, GPU info)
- Relevant log output

## Architecture

Familiarize yourself with the project structure before contributing:

- `backend/app/services/` — Core business logic (LLM, RAG, agents, voice)
- `backend/app/api/routes/` — API endpoint definitions
- `backend/app/models/` — SQLAlchemy ORM models
- `frontend/src/components/` — React UI components
- `frontend/src/store/` — Zustand state management
- `infra/` — Docker, Kubernetes, Nginx, monitoring configs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
