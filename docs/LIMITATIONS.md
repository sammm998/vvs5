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
  unknown characters are never repaired from expected words. The one exception is a character whose ink is cut
  by a clipping edge of the drawing (a sheet-part boundary that halves a label): the truncated character is
  completed from what this drawing itself writes, and only when one reading dominates the alternatives.
* **Hatched areas** are detected as regularly spaced parallel strokes and pipe inside them is measured but held
  out of the total. The engine cannot tell a wall section from a large area hatch marking an adjacent sheet part,
  so on a sheet that hatches most of its plan (drawing W-50-1-A-0014: 39 m hatched against 48 m outside) the
  operator decides with the "Räkna med skrafferade ytor" checkbox.
* **Open-world drawing D** (ground-heating site plan, 1:400): labels are zone descriptions without DN, placed on
  unlabeled loop pipes; no VVS designation grammar exists, so no pipes are owned. The engine reports UNSUPPORTED
  structure and zero false ownership. Post-freeze, per-glyph O/0 twin substitution lets the vector scale bar
  (0 5 10 20 30 METER) be read (BAR_ONLY, 1:400).
* **Unreadable characters are only partly recoverable.** The OCR-assisted pass fills a '?' only where OCR reads
  the same word and agrees with it character for character. On dense drawings much of the small text is beyond
  OCR too, so unreadable characters remain; the unresolved list now says how many sit inside a designation (which
  costs a takeoff row) and how many sit in legend or note text (which costs nothing).
* **The review agents are deterministic checks, not a language model.** They compare the result against the
  drawing's own evidence and report where to look; they do not reason about intent, and they never edit a
  measurement. The OCR cross-check reads the rendered page only to ask whether a designation exists where the
  vector reading has none - it never contributes a metre.
* **Scanned drawings are not analysed.** Only vector PDFs are read. A scanned or image-only page is classified,
  skipped and reported; a PDF with no vector page is rejected. Measuring a scan means inferring geometry from
  pixels, and on these drawings that produced errors large enough to be misleading, so the engine says no instead.
* **Docker images** could not be built inside the development container (no Docker daemon); the Dockerfiles and
  compose file are provided as written and the backend/frontend were verified with pytest and `npm run build`.
* Multi-page PDFs are analysed page by page; overlays and artifacts are written for page 0 (the first analysed page)
  in the CLI and web application.
