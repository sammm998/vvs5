# Known limitations (state at the open-world gate)

* **Vertical quantities**: the drawing carries no floor height, so the engine never invents vertical metres. It
  counts risers per designation (closed riser marks a label points at, marks of the same riser-mark family at the
  end of or on a pipe, count prefixes such as `5x` for marker stacks) and reports `riser_count`; the application
  turns risers into vertical metres only with a floor height the user enters (Excel/CSV export accept
  `floor_height`). Elevation pairs (VG/CL) on one pipe still give measured vertical metres. Riser counts follow the
  drawn marks: tiny end circles without a label (fixture connection points) are not risers; a label pointing at a
  connection mark still counts it. On drawing A this gives 55 risers against 54 in the reference takeoff, with
  per-system differences (KV2/VV1 7 vs 5 counted from the labelled end marks, S3-R8-75 28 vs 35 where seven riser
  marks sit on short unowned stubs).
* **Hatched areas** (regularly spaced parallel strokes: wall sections, existing parts) are discovered per drawing;
  pipe length inside them is measured but excluded from the horizontal quantity and reported as
  `in_hatched_area_m` ("varav i skrafferat område"), since takeoffs normally do not count pipe in walls.
* **DN transitions** are placed only at drawn evidence: the tick mark at a leader end on the pipe. Between two labels
  of different DN the geometry belongs to the label whose tick is not the boundary; when both (or neither) carry a
  tick and no dead end decides, the run is AMBIGUOUS_DN_BOUNDARY. A tick in the middle of a branch that continues
  past it (DN change or plain pointer, undecidable) makes the part between junction and tick AMBIGUOUS.
  Reducer symbols are not recognised as proof of a transition point.
* **Label-vs-takeoff convention on dead-end stubs**: a stub labelled DN75 with its tick right after the junction is
  owned as DN75 from that tick (label evidence). A human takeoff may count the stub as the main DN up to the last
  tick before the riser; the engine does not guess and reports the label's reading.
* **Unlabeled branches** at junctions stay AMBIGUOUS_BRANCH with candidate identities; only collinear straight-through
  runs, agreeing anchors, and the junction's own DN up to a drawn tick continue ownership through junctions.
* **Bundle labels** (one leader crossing N pipes with N stacked rows) are resolved through drawing-local layer-name
  tokens (exact, wildcard, or abbreviated tail such as KV2 -> V2), a unique parallel-line count bijection, or the row
  whose own underline the leader starts from; a bundle with two rows of the same system and different DN on the same
  layer stays ambiguous. Runs interrupted by symbol groups (stacked valve/coupling circles) are not bridged through
  the symbols: the geometry beyond the symbol group stays UNNAMED unless it carries its own label.
* **Count prefixes** ("5xKV2-X31") are read and recorded as the label's multiplier; quantities count the pipes actually
  drawn and attached (parallel lines), never the multiplier times one line.
* **Stroke-font recognition** relies on generic reference alphabets (Hershey simplex/duplex, Helvetica, Courier,
  Times skeletons). Very small text (< 2.5 pt on the page) and exotic CAD fonts produce unknown glyphs ('?');
  unknown characters are never repaired from expected words.
* **Open-world drawing D** (ground-heating site plan, 1:400): labels are zone descriptions without DN, placed on
  unlabeled loop pipes; no VVS designation grammar exists, so no pipes are owned. The engine reports UNSUPPORTED
  structure and zero false ownership. Post-freeze, per-glyph O/0 twin substitution lets the vector scale bar
  (0 5 10 20 30 METER) be read (BAR_ONLY, 1:400).
* **Scanned drawings** are supported through vectorisation + OCR, not at vector fidelity: traced dashes lose about
  half a stroke width at each end, crossings become junctions, OCR confuses 0/O, 1/I/T and drops very small digits,
  and layer names do not exist, so pipe families are accepted from leader-end evidence only. On a 300 dpi scan of
  drawing A: 139 designations (139 in the vector original), scale VERIFIED, 72 verified attachments, 114 m confirmed + 30 m ambiguous against
  210 m from the vector original. Results carry `input.mode = raster` and an OCR confidence report.
* **Docker images** could not be built inside the development container (no Docker daemon); the Dockerfiles and
  compose file are provided as written and the backend/frontend were verified with pytest and `npm run build`.
* Multi-page PDFs are analysed page by page; overlays and artifacts are written for page 0 (the first analysed page)
  in the CLI and web application.
