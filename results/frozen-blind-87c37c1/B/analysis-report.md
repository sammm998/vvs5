# Analysis report: DRAWING_B

## Status
- designations: 151 (with DN 111)
- actual CAD leaders: 101 (from designation blocks: 70)
- pipe attachments: verified 49, ambiguous 19, none 47
- physical pipes: 58
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 29976.141 pt = confirmed 5713.495 + ambiguous 342.428 + unowned 23920.218)
- determinism: PASS
- contamination: PASS
- runtime: 86.3 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV01-X32 | 25 | 2 | 0.38 | UNKNOWN | 0.38 | 0.00 | CONFIRMED |
| KV01-X7-20-W40 | 20 | 2 | 0.87 | UNKNOWN | 0.87 | 0.00 | CONFIRMED |
| KV01-X7-25-W40 | 25 | 3 | 5.48 | UNKNOWN | 5.48 | 0.57 | CONFIRMED |
| KV01-X7-32-W40 | 32 | 2 | 0.76 | UNKNOWN | 0.76 | 0.00 | CONFIRMED |
| KV01-X7-40-W40 | 40 | 1 | 17.37 | UNKNOWN | 17.37 | 0.00 | CONFIRMED |
| KV02-X32 | 25 | 1 | 0.15 | UNKNOWN | 0.15 | 0.00 | CONFIRMED |
| S01-P5-160 | 160 | 1 | 10.36 | 0.10 | 10.46 | 0.00 | CONFIRMED |
| S01-P5 | 75 | 1 | 0.15 | UNKNOWN | 0.15 | 0.00 | CONFIRMED |
| SF01-P5-110 | 110 | 2 | 0.92 | UNKNOWN | 0.92 | 0.00 | CONFIRMED |
| SF01-P5-160 | 160 | 1 | 0.38 | UNKNOWN | 0.38 | 0.00 | CONFIRMED |
| SF01-P5 | 75 | 7 | 4.24 | UNKNOWN | 4.24 | 2.75 | CONFIRMED |
| VP01-S2-65-F80 | 65 | 4 | 35.09 | UNKNOWN | 35.09 | 0.00 | CONFIRMED |
| VS21-S13-15-F50 | 15 | 5 | 10.15 | UNKNOWN | 10.15 | 0.00 | CONFIRMED |
| VS21-S13 | 15 | 13 | 9.13 | UNKNOWN | 9.13 | 1.82 | CONFIRMED |
| VS31-S13-28-F60 | 28 | 4 | 36.74 | UNKNOWN | 36.74 | 0.00 | CONFIRMED |
| VS31-X32 | ? | 2 | 0.62 | UNKNOWN | 0.62 | 0.00 | CONFIRMED |
| VV01-X32 | 25 | 2 | 0.33 | UNKNOWN | 0.33 | 0.00 | CONFIRMED |
| VV01-X7-25-F60 | 25 | 2 | 1.01 | UNKNOWN | 1.01 | 0.74 | CONFIRMED |
| VV01-X7-32-F60 | 32 | 1 | 0.41 | UNKNOWN | 0.41 | 0.00 | CONFIRMED |
| VVC01-X7-20 | 20 | 2 | 2.54 | UNKNOWN | 2.54 | 0.22 | CONFIRMED |

Totals: confirmed horizontal 137.08 m, ambiguous 6.10 m, unowned pipe geometry 425.93 m

## Unresolved
- unknown_glyph: 101
- missing_dn: 40
- missing_leader: 48
- ambiguous_pipe_attachment: 19
- missing_pipe_attachment: 47
- topology_conflict: 1
- branch_conflict: 6
- unowned_geometry: 13

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
