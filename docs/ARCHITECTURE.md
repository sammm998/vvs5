# Architecture

## Semantic pipeline (authoritative order)

```
RAW PDF VECTOR OBJECTS  (vvs_engine/pdf/extract.py: paths, segments, flattened curves, transforms, XObjects, OCG layers, searchable text)
  -> DRAWING PROFILE / VECTOR GRAMMAR  (profile/layers.py + statistics gathered by every stage; drawing-profile.json)
  -> CAD / VECTOR STRUCTURAL FAMILIES  (layer|style families; roles are derived from evidence, never from fixed layer names)
  -> VVS ANNOTATION POPULATION  (semantics/annotation.py: lines -> blocks -> label units, underlines, boxes)
  -> PDF TEXT OR VECTOR GLYPHS  (text/searchable.py; text/strokes.py + text/recognize.py: components -> glyphs -> shape families -> characters)
  -> VISIBLE VVS DESIGNATION  (semantics/grammar.py: drawing-local code STRUCTURE, twin-shape resolution by pattern frequency)
  -> DN  (inline token position accepted per grammar family via the generic nominal-size series, or an underlined DN row)
  -> ACTUAL CAD LEADER  (semantics/leaders.py: chains of real segments starting at block boundary points; tick markers)
  -> LEADER ENDPOINT + PIPE ATTACHMENT  (semantics/attachment.py: contacts at endpoint / crossing ticks; layer-token or count bijection; marker/fitting bridges)
  -> PIPE REPRESENTATION + TOPOLOGY  (pipes/representation.py: micro-gap families, T-junction splitting, crossing != connection)
  -> PHYSICAL PIPE  (pipes/ownership.py: chain-wise ownership, agreeing anchors, DN boundaries, collinear continuation, AMBIGUOUS_BRANCH)
  -> MEASUREMENT  (measure/scale.py: scale text + vector scale bar; measure/measure.py: horizontal from actual geometry, vertical only with explicit evidence)
  -> QUANTITY  (aggregate by designation base + DN; ambiguous reported separately)
  -> ARTIFACTS  (output/artifacts.py, output/overlays.py; reconcile.py; determinism.py; contamination.py)
```

## Bootstrapping without prior knowledge

1. Pass 1: leaders from any thin geometry attached to designation blocks. Their endpoint/tick contacts vote for
   vector families. Families become pipe geometry only if they are chain-like AND (their layer name carries the
   designation's system token, or they are template-similar to such layers, or tick evidence is strong).
2. The verified attachments of pass 1 reveal the drawing's annotation families (leader/frame/glyph layer+style).
3. Pass 2 repeats leaders/attachments restricted to those families. Nothing is persisted between drawings.

## States

Attachment: VERIFIED_PIPE_ATTACHMENT | AMBIGUOUS_PIPE_ATTACHMENT | NO_PIPE_ATTACHMENT (machine-readable reason).
Primitive ownership: CONFIRMED | AMBIGUOUS (candidates + reason: AMBIGUOUS_BRANCH, AMBIGUOUS_DN_BOUNDARY, SYSTEM_CONFLICT) | UNOWNED.
Scale: VERIFIED | TEXT_ONLY | BAR_ONLY | CONFLICT | NONE. Vertical: value with evidence or UNKNOWN.

## Application

FastAPI (`backend/app`): JWT auth, project ownership isolation, drawing upload, background analysis jobs with real
stage progress, artifact/why/export endpoints. Storage abstraction (`storage.py`) with a local backend; the same
interface maps to an object store. React/TypeScript (`frontend/src`): PDF.js viewer with an SVG overlay in PDF
coordinates, quantity table (search/filter/sort, click-sync with pipes), "Ej lösta" issue list with zoom-to-location,
overview KPIs, exports.
