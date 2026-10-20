# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

skeleton

## Roadmap

### skeleton — FastAPI/React skeleton with Docker, CI, and auth baseline

Status: in_progress

Acceptance:
- Backend FastAPI app starts and serves /health endpoint
- Frontend React/Vite app builds and serves
- Docker compose brings up backend, frontend, Keycloak, and SQLite
- CI workflow runs backend tests, frontend build/test, and Docker builds
- OIDC Keycloak auth with PKCE flow implemented (backend sessions + HttpOnly cookies)
- SQLite persistence with migrations
- README with install/run/test steps

### model-registry — Model registry with metadata, search, and import workflow

Status: planned

Acceptance:
- API: CRUD for model records (name, architecture, quantization, hardware profile)
- UI: Model list with filtering, detail view, create/import modal
- Import from HuggingFace Hub (metadata only, no weights)
- Persistent storage with audit log

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

