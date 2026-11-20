# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

skeleton

## Roadmap

### skeleton — FastAPI/React skeleton with Docker, CI, and auth baseline

Status: done

Acceptance:
- Backend FastAPI app starts and serves /health endpoint
- Frontend React/Vite app builds and serves
- Docker compose brings up backend, frontend, Keycloak, and SQLite
- CI workflow runs backend tests, frontend build/test, and Docker builds
- OIDC Keycloak auth with PKCE flow implemented (backend sessions + HttpOnly cookies)
- SQLite persistence with migrations
- README with install/run/test steps

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/api/health.py`, `backend/app/api/auth.py`, `backend/app/api/models.py`, `backend/app/api/benchmarks.py`, `backend/app/api/hardware.py`, `backend/app/api/deps.py`, `backend/app/models/__init__.py`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Models.tsx`, `frontend/src/pages/Benchmarks.tsx`, `frontend/src/pages/Hardware.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/LoginCallback.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/hooks/useAuth.ts`, `compose.yaml`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_all.py`

### model-registry — Model registry with metadata, search, and import workflow

Status: done

Acceptance:
- API: CRUD for model records (name, architecture, quantization, hardware profile)
- UI: Model list with filtering, detail view, create/import modal
- Import from HuggingFace Hub (metadata only, no weights)
- Persistent storage with audit log

Implementation: `backend/app/api/models.py - CRUD endpoints (list, get, create, update, delete, import)`, `backend/app/models/__init__.py - Model ORM with name, architecture, quantization, hardware_profile, huggingface_repo, description, config_json, is_active`, `frontend/src/pages/Models.tsx - Model list with filtering, create/import modals, delete`

Tests: `backend/tests/test_all.py - TestModelsIsActive (is_active filter tests)`

### inference-benchmark — Inference benchmark engine (offline, deterministic)

Status: planned

Acceptance:
- Core engine: token throughput, latency (TTFT, TPOT), memory tracking
- Runs without LLM key (deterministic synthetic workload)
- API: start benchmark, poll status, fetch results
- UI: Benchmark dashboard with charts from real API data
- Export results (JSON/CSV)

### hardware-profiling — Hardware capability detection and profiling

Status: planned

Acceptance:
- Detect GPU arch (SM version), VRAM, driver/CUDA version
- Profile kernel compatibility for target models
- API/UX: hardware profile CRUD, compatibility matrix

### llm-advisory — Opt-in LLM advisory explanations

Status: planned

Acceptance:
- Configurable provider (OpenAI-compatible, Anthropic, Gemini, Ollama)
- Advisory badge on all LLM outputs
- Grounded in actual benchmark/hardware records
- Clear provider errors, no fabricated responses

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
