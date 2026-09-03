# VVS Mängdning – drawing-adaptive automatic pipe takeoff for clean vector VVS PDFs

One generic engine discovers, per drawing, how the PDF represents layers, text (searchable or open-stroke
CAD glyphs), VVS designations, DN, leaders, markers, pipes, topology and scale, then reconstructs
PhysicalPipes with a full evidence chain (RAW PDF OBJECT → family → glyph/text → designation → DN → actual
leader → endpoint → pipe attachment → topology → physical pipe → scale → measurement).

```
engine/          Python engine (vvs_engine) + CLI + tests
backend/         FastAPI application (auth, projects, drawings, background analysis jobs, exports)
frontend/        React + TypeScript (Vite) web UI in Swedish with a PDF.js viewer
docker/          Dockerfiles + nginx config; docker-compose.yml at the root
results/         Frozen artifacts for the development drawings (A, B, C) and the open-world drawing (D)
data/dev/        The three clean development drawings (A, B, C)
```

## Install and run locally

```bash
# engine
pip install -e engine          # pymupdf, shapely, numpy, scipy
vvs-takeoff analyze data/dev/DRAWING_A.pdf --out results/A --name DRAWING_A
vvs-takeoff why data/dev/DRAWING_A.pdf <physical_pipe_id>

# tests (engine + API)
cd engine && python -m pytest -q tests

# backend (SQLite by default; see .env.example for PostgreSQL)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

## Complete application with Docker

```bash
cp .env.example .env            # optional
docker compose up --build       # web UI on http://localhost:8080, API on http://localhost:8000, PostgreSQL inside
```

Workflow: skapa projekt → ladda upp VVS-PDF → analysera → följ förloppet → inspektera ritning och mängder →
Ej lösta → ladda ner markerad PDF / Excel / CSV / JSON / analysrapport.

## Artifacts per drawing (results/<name>/)

drawing-profile.json, drawing-profile-report.md, raw-vector-inventory.json, cad-layer-map.json,
vector-designations.json, designation-overlay.pdf, leader-forensics.json, leader-family-report.json,
pipe-code-anchors.json, endpoint-pipe-attachment-overlay.pdf, pipe-representation-families.json,
pipe-geometry-inventory.json, pipe-topology.json, physical-pipes.json, quantities.json, unresolved-issues.json,
evidence-graph.json, reconciliation.json, determinism.json, contamination-report.json, performance-report.json,
production-overlay.pdf (+ topology/ambiguous/unsupported-style overlays), analysis-report.md, freeze-manifest.json.

## Principles enforced by the engine

* Identity comes from the visible designation and its ACTUAL vector leader, never from nearest-text/pipe logic.
* DrawingProfile is derived from the PDF only, per analysis job; nothing persists between drawings.
* Ambiguity is a valid result (AMBIGUOUS_* states with machine-readable reasons); wrong certainty is not.
* Geometry conservation: raw pipe geometry = confirmed + ambiguous + unowned, no double counting (reconciliation.json).
* Determinism: original / reversed / two shuffled object orders give identical semantic results (determinism.json).
* Contamination firewall: the production package is scanned for drawing-specific literals and never imports validation data.
