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

## Deploy as one container (Railway, any Docker host)

The root `Dockerfile` builds the frontend, installs the engine and the API and serves the built frontend from
FastAPI (`railway.json` points Railway at it). Environment: `PORT` (honoured), `VVS_SECRET_KEY`, optionally
`VVS_DATABASE_URL` (PostgreSQL) and a volume at `/data` for uploads and the SQLite database.

## Scanned / rasterised drawings

Every page is classified from its own content (`vvs_engine/pdf/classify.py`): vector paths and text characters
against embedded images and their page coverage. A clean vector page goes straight to the vector engine. A page
that is only an image (scan, rasterised export) goes through the raster path (`vvs_engine/raster/`): the page is
binarised, its text is read with OCR (RapidOCR, ONNX on CPU, tiled at 300 dpi), glyph ink is masked out, the
remaining ink is skeletonised and traced into stroke polylines with measured widths, and drawing-local width
classes become the vector families. From there the same designation grammar, leader, attachment, topology,
ownership and measurement code runs unchanged. The result is labelled "skannad/rastrerad (OCR)" with the OCR
confidence and the share of ink explained by traced strokes; expect lower fidelity than a vector PDF (on a 300 dpi
scan of drawing A the engine reads 139 designations, as many as the vector original, verifies the scale, attaches 72 labels and owns about
half of the pipe length that the vector original yields, with a further seventh reported as ambiguous), and check
designations and scale in the "Ej lösta" view.

## Quantities: horizontal, hatched areas, risers

* Horizontal metres are measured from the pipe geometry outside hatched areas; pipe running through hatched areas
  (wall sections, adjacent sheet parts) is measured too and reported separately as "varav i skrafferat område".
  It stays out of the total unless the checkbox "Räkna med skrafferade ytor" is ticked (`?include_hatched=true` on
  Excel/CSV export). Measuring the reference markup of drawing A shows the takeoff excludes it: 0.25 m of 213.4 m.
* Risers are counted from the drawn riser marks per designation. The drawing carries no floor height, so vertical
  metres are computed only when the user enters a floor height (Mängder tab; `?floor_height=` on Excel/CSV export).
* DN changes are placed at drawn tick marks; labels pointing at a riser mark describe the riser, not the run.

## Scale

The scale is read from the drawing and never assumed. A printed ratio ("1:50") is exact; a drawn scale bar is
measured from the bar's own extent rather than from its label glyph centres, which sit a fraction of a character
off the graduations (that error was 0.95 % on these drawings). When a sheet states one ratio per print format
("SKALA A1 (A3)" over "1:50 (1:100)"), the k-th format belongs to the k-th ratio and the sheet's own size selects
the one that applies. Two ratios with nothing to separate them stay a CONFLICT and no scale is assumed.

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
