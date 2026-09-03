# Analysis report: DRAWING_C

## Status
- designations: 45 (with DN 36)
- actual CAD leaders: 19 (from designation blocks: 15)
- pipe attachments: verified 23, ambiguous 2, none 3
- physical pipes: 31
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 8448.6 pt = confirmed 3918.222 + ambiguous 193.159 + unowned 4337.219)
- determinism: PASS
- contamination: PASS
- runtime: 38.4 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV01-X7-40-W40 | 40 | 3 | 14.90 | UNKNOWN | 14.90 | 0.00 | CONFIRMED |
| S01-P5-160 | 160 | 1 | 2.37 | UNKNOWN | 2.37 | 0.00 | CONFIRMED |
| VP01-S2-65-F80 | 65 | 5 | 18.52 | UNKNOWN | 18.52 | 0.00 | CONFIRMED |
| VS21-S13-15-F50 | 15 | 2 | 12.37 | 0.50 | 12.87 | 1.65 | CONFIRMED |
| VS21-S13 | 15 | 6 | 3.32 | UNKNOWN | 3.32 | 1.78 | CONFIRMED |
| VS31-S13-28-F60 | 28 | 6 | 13.66 | UNKNOWN | 13.66 | 0.00 | CONFIRMED |
| VS31-X32 | 25 | 2 | 0.64 | UNKNOWN | 0.64 | 0.00 | CONFIRMED |
| VV01-X7-40-F60 | 40 | 3 | 14.12 | UNKNOWN | 14.12 | 0.00 | CONFIRMED |
| VVC01-X7-32 | 32 | 3 | 15.75 | UNKNOWN | 15.75 | 0.00 | CONFIRMED |

Totals: confirmed horizontal 95.65 m, ambiguous 3.44 m, unowned pipe geometry 77.23 m

## Unresolved
- unknown_glyph: 69
- missing_dn: 9
- missing_leader: 17
- missing_pipe_attachment: 3
- ambiguous_pipe_attachment: 2
- unowned_geometry: 7
- branch_conflict: 2

## Artifacts
- ambiguous-overlay.pdf
- cad-layer-map.json
- contamination-report.json
- designation-overlay.pdf
- determinism.json
- drawing-profile-report.md
- drawing-profile.json
- endpoint-pipe-attachment-overlay.pdf
- evidence-graph.json
- leader-family-report.json
- leader-forensics.json
- leader-overlay.pdf
- performance-report.json
- physical-pipes.json
- pipe-code-anchors.json
- pipe-geometry-inventory.json
- pipe-representation-families.json
- pipe-topology.json
- production-overlay.pdf
- quantities.json
- raw-vector-inventory.json
- reconciliation.json
- topology-overlay.pdf
- unresolved-issues.json
- unsupported-style-overlay.pdf
- vector-designations.json
