# Known limitations (state at the open-world gate)

* **Vertical quantities** are produced only when two elevation annotations with the same tag (VG, CL, ...) sit on
  the anchors of one physical pipe; riser symbols and section relationships are not interpreted. Most pipes therefore
  report `vertical_m = UNKNOWN` (honest, not fabricated).
* **DN transitions without a second label** cannot be split: the run between two labels of different DN is
  reported as AMBIGUOUS_DN_BOUNDARY; reducer symbols are not recognised as proof of the transition point.
* **Unlabeled branches** at junctions stay AMBIGUOUS_BRANCH with candidate identities; only collinear straight-through
  runs and agreeing anchors continue ownership through junctions.
* **Bundle labels** (one leader crossing N pipes with N stacked rows) are resolved through drawing-local layer-name
  tokens or a unique parallel-line count bijection; a bundle with two rows of the same system and different DN on the
  same layer stays ambiguous.
* **Stroke-font recognition** relies on generic reference alphabets (Hershey simplex/duplex, Helvetica, Courier,
  Times skeletons). Very small text (< 2.5 pt on the page) and exotic CAD fonts produce unknown glyphs ('?');
  unknown characters are never repaired from expected words.
* **Open-world drawing D** (ground-heating site plan, 1:400): labels are zone descriptions without DN, placed on
  unlabeled loop pipes; no VVS designation grammar exists, so no pipes are owned. The engine reports UNSUPPORTED
  structure and zero false ownership. Post-freeze, per-glyph O/0 twin substitution lets the vector scale bar
  (0 5 10 20 30 METER) be read (BAR_ONLY, 1:400).
* **Docker images** could not be built inside the development container (no Docker daemon); the Dockerfiles and
  compose file are provided as written and the backend/frontend were verified with pytest and `npm run build`.
* Multi-page PDFs are analysed page by page; overlays and artifacts are written for page 0 (the first analysed page)
  in the CLI and web application.
