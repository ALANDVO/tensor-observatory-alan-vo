# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Tensor Observatory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-20

### Added
- Initial project scaffold with FastAPI backend and React/Vite frontend
- Keycloak OIDC authentication with PKCE, HttpOnly session cookies, and CSRF protection
- Role-based access control (viewer, operator, admin)
- Model registry with CRUD, HuggingFace Hub metadata import, and audit logging
- Deterministic benchmark engine (synthetic workloads, token throughput, TTFT, TPOT, memory)
- Hardware profile management (GPU model, count, SM version, VRAM, driver/CUDA)
- Model-hardware compatibility matrix with status tracking
- SQLite persistence with SQLAlchemy async and Alembic migrations
- Docker Compose with backend, frontend, Keycloak, and persistent volumes
- CI/CD workflow (backend tests, frontend build/test, Docker builds)
- Comprehensive documentation (README, API reference, security, deployment)
- MIT License and portfolio.json metadata

### Security
- JWT validation with RS256, issuer/audience/nonce verification
- JWKS caching with 1-hour TTL
- HttpOnly, SameSite=Lax session cookies
- Double-submit CSRF token pattern
- No hardcoded secrets or demo mode in production

### Infrastructure
- Non-root Docker users
- Health checks on all services
- Development ports bound to 127.0.0.1
- .env.example with blank credentials
- .gitignore for dependencies, databases, and local config

---

## [Unreleased]

### Planned
- Model detail view with config JSON visualization
- Benchmark results visualization (charts from API data)
- Export benchmarks to JSON/CSV
- Hardware auto-detection (nvidia-smi integration)
- LLM advisory explanations (opt-in, provider-adapter pattern)
- Prefix caching compatibility tracking
- Multi-node benchmark orchestration
- PostgreSQL migration for production