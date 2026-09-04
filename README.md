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

## What a vector PDF actually contains

Worth being precise about, because it decides what is readable and what must be recognised. Drawing A's content
stream holds 74 976 `l`, 33 081 `m`, 18 459 `S` and 7 649 `c` operators - and 17 text-show operators, 88
characters in total: the grid bubbles (A2, A00, A100, A200, 00, 2, 70, 140, 210) and the revision table. Not one
pipe designation. W-50-1-A-0014 has four text operators, 27 characters.

The CAD export exploded every label into line geometry. `S1-P2-110` is not the string "S1-P2-110" anywhere in the
file; it is a few dozen `m`/`l` pairs. There is no character code to read, so each character has to be recognised
from the shape its strokes make - which is what the engine does, and where an unnamed '?' comes from.

The drawing does embed the typeface it drew with (ISOCPEUR), and those glyph shapes join the reference alphabet as
the drawing's own evidence. The embedded copy is subset to the characters its remaining real text uses, though -
16 of them on drawing A, none of which are the S, R, V or K a designation needs - so it helps less than it sounds.

## Vector PDFs only

The engine reads the drawing's own vector content: every path operator with its segments, layer, stroke width and
colour, plus the text objects and the stroke-font glyph outlines. Nothing is inferred from a rendered image, and
there is no OCR anywhere in the pipeline.

Every page is therefore classified first (`vvs_engine/pdf/classify.py`) from vector paths and text characters
against embedded images and their page coverage. A vector page is analysed; a scanned or image-only page is
skipped and reported, and a PDF with no vector page at all is rejected with `UnsupportedInputError` rather than
measured from pixels. In the web application that becomes a plain message: export the drawing as a vector PDF
from CAD instead of scanning it.

## Quantities: horizontal, hatched areas, risers

* Horizontal metres are measured from the pipe geometry outside hatched areas; pipe running through hatched areas
  (wall sections, adjacent sheet parts) is measured too and reported separately as "varav i skrafferat område".
  It stays out of the total unless the checkbox "Räkna med skrafferade ytor" is ticked (`?include_hatched=true` on
  Excel/CSV export). Measuring the reference markup of drawing A shows the takeoff excludes it: 0.25 m of 213.4 m.
* Two label forms mean two different things: a dimension inline ("S3-R8-75") names the horizontal run, a
  dimension on the row below ("S3-R8" over "75") names the vertical pipe at that point. A count prefix is the
  exception - "2xKV1-X31" over "16" bundles parallel pipes along the run, and the reference takeoff of drawing A
  gives that label no vertical metres. Both riser sources are reported per row and the operator picks which one
  the vertical quantity uses. Labels are the default: on W-50-1-A-0012 they give exactly the reference's 2 + 2
  where the drawn symbols give 1 + 0, and on drawing A the two are equally far off overall (deviation 20 against
  21 across the nine identities) while the labels match four identities exactly that the symbols get wrong.
* Risers are counted from the drawn riser marks per designation. The drawing carries no floor height, so vertical
  metres are computed only when the user enters a floor height (Mängder tab; `?floor_height=` on Excel/CSV export).
* DN changes are placed at drawn tick marks; labels pointing at a riser mark describe the riser, not the run.
* Dashed runs are chained across the line style's own gap, including where the run turns a corner inside a gap:
  the two free ends' outward rays must meet one gap away, which is the drawing's own evidence for the bend.
* A branch with no size label of its own, off a junction where every labelled arm carries the same identity, is
  that identity: a size change is always drawn with its own label. A junction with two competing identities leaves
  the branch AMBIGUOUS rather than guessing.
* Every designation gets its own colour, the same one in the viewer and in the exported marked PDF. No colour is
  dark enough to be mistaken for the drawing's own black line work.

## Scale

The scale is read from the drawing and never assumed. A printed ratio ("1:50") is exact; a drawn scale bar is
measured from the bar's own extent rather than from its label glyph centres, which sit a fraction of a character
off the graduations (that error was 0.95 % on these drawings). When a sheet states one ratio per print format
("SKALA A1 (A3)" over "1:50 (1:100)"), the k-th format belongs to the k-th ratio and the sheet's own size selects
the one that applies. Two ratios with nothing to separate them stay a CONFLICT and no scale is assumed.

## Review agents

Every analysis is checked afterwards by agents that do not trust it (`vvs_engine/review/`). They report findings
with a severity, a place to look and the numbers behind the verdict; none of them may change a measurement, since
a review that could edit the result would hide the disagreement it exists to surface.

* **scale** - is there a scale, does a bar confirm it, is the ratio a plausible one
* **coverage** - how much of the accepted pipe geometry actually ended up owned by a designation
* **plausibility** - sizes against the nominal series, lengths against the drawing's own extent, rows without DN
* **topology** - free pipe ends and runs left between two possible designations
* **designations** - labels with a dimension that never reached a pipe, unreadable characters
* **ocr_crosscheck** - the page is rendered and read with OCR as an independent second opinion. It never feeds the
  measurement: it only asks whether OCR sees a designation, in the drawing's own label pattern, where the vector
  reading has no text at all. On drawings A and W-50-1-A-0014 it finds none, which is the confirmation that the
  vector reading missed nothing. Needs the `review` extra (`pip install -e engine[review]`); without it the agent
  reports that the cross-check did not run. Disable with `VVS_REVIEW_OCR=false`, the whole layer with
  `VVS_RUN_REVIEW=false`.

The findings are written to `review-findings.json` and shown in the application's "Granskning" tab.

### Resolving what the vector reader could not name

Where a glyph's shape matches no reference letter the row keeps a '?', and everything built on it - the
designation, its dimension, the pipe it labels - is lost. An opt-in pass (`VVS_OCR_ASSIST`, on by default when the
`review` extra is installed) renders the page, reads it in overlapping tiles and fills in those positions, but only
where an OCR word lines up character for character with a vector-read word and agrees everywhere both readings are
sure. Every adopted character is written to `ocr-assisted-characters.json` with its confidence and position.

It resolves what OCR can actually see and no more: on drawing A it named 18 of 56 unreadable characters, on
drawings C and W-50-1-A-0014 none, because OCR finds no text at those positions either. The measured quantities on
all three are unchanged, since those characters sit in legend text and notes rather than in designations.

## Validation against reference takeoffs

Two drawings have a reference takeoff (`results/validation/`). Neither is read by production code; the
contamination scan fails the build if the package ever imports from the validation directories.

| | reference H | engine H | deviation | reference vertical | from labels | from symbols |
|---|---|---|---|---|---|---|
| W-50-1-A-0011 (full markup) | 213.4 m | 212.0 m | -0.6 % | 55 | 41 | 58 |
| W-50-1-A-0012 (two systems) | 17.6 m | 17.2 m | -2.1 % | 4 | 4 | 1 |

On both, sampling the reference polylines every point shows the engine owns essentially all of the geometry they
mark: 213.10 m of 213.38 m on the first, 17.46 m of 17.72 m on the second, with the remainder inside hatching or
at run ends where the reference clicks a point or two past where the drawn line stops.

## Artifacts per drawing (results/<name>/)

drawing-profile.json, drawing-profile-report.md, raw-vector-inventory.json, cad-layer-map.json,
vector-designations.json, designation-overlay.pdf, leader-forensics.json, leader-family-report.json,
pipe-code-anchors.json, endpoint-pipe-attachment-overlay.pdf, pipe-representation-families.json,
pipe-geometry-inventory.json, pipe-topology.json, physical-pipes.json, quantities.json, unresolved-issues.json,
evidence-graph.json, reconciliation.json, review-findings.json, ocr-assisted-characters.json, determinism.json, contamination-report.json, performance-report.json,
production-overlay.pdf (+ topology/ambiguous/unsupported-style overlays), analysis-report.md, freeze-manifest.json.

## Principles enforced by the engine

* Identity comes from the visible designation and its ACTUAL vector leader, never from nearest-text/pipe logic.
* DrawingProfile is derived from the PDF only, per analysis job; nothing persists between drawings.
* Ambiguity is a valid result (AMBIGUOUS_* states with machine-readable reasons); wrong certainty is not.
* Geometry conservation: raw pipe geometry = confirmed + ambiguous + unowned, no double counting (reconciliation.json).
* Determinism: original / reversed / two shuffled object orders give identical semantic results (determinism.json).
* Contamination firewall: the production package is scanned for drawing-specific literals and never imports validation data.
