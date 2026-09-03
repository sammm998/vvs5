# Analysis report: DRAWING_B

## Status
- designations: 152 (with DN 111)
- actual CAD leaders: 183 (from designation blocks: 80)
- pipe attachments: verified 60, ambiguous 23, none 42
- physical pipes: 75
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 29193.04 pt = confirmed 7359.961 + ambiguous 340.764 + unowned 21492.315)
- determinism: PASS
- contamination: PASS
- runtime: 87.8 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV01-X32 | 25 | 2 | 0.38 | UNKNOWN | 0.38 | 0.00 | CONFIRMED |
| KV01-X7-20-W40 | 20 | 3 | 1.20 | UNKNOWN | 1.20 | 0.00 | CONFIRMED |
| KV01-X7-25-W40 | 25 | 3 | 5.48 | UNKNOWN | 5.48 | 0.57 | CONFIRMED |
| KV01-X7-32-W40 | 32 | 2 | 0.76 | UNKNOWN | 0.76 | 0.00 | CONFIRMED |
| KV01-X7-40-W40 | 40 | 1 | 17.37 | UNKNOWN | 17.37 | 0.00 | CONFIRMED |
| KV02-X32 | 25 | 1 | 0.15 | UNKNOWN | 0.15 | 0.00 | CONFIRMED |
| S01-P3S01-P3 | 110 | 1 | 0.05 | UNKNOWN | 0.05 | 0.00 | CONFIRMED |
| S01-P5-160 | 160 | 1 | 10.36 | 0.10 | 10.46 | 0.00 | CONFIRMED |
| S01-P5 | 75 | 1 | 0.15 | UNKNOWN | 0.15 | 0.00 | CONFIRMED |
| SF01-P3 | 75 | 4 | 1.23 | UNKNOWN | 1.23 | 0.00 | CONFIRMED |
| SF01-P5-110 | 110 | 2 | 0.92 | UNKNOWN | 0.92 | 0.00 | CONFIRMED |
| SF01-P5-160 | 160 | 1 | 0.38 | UNKNOWN | 0.38 | 0.00 | CONFIRMED |
| SF01-P5 | 75 | 8 | 5.21 | UNKNOWN | 5.21 | 2.75 | CONFIRMED |
| VP01-S2-65-F80 | 65 | 4 | 35.09 | UNKNOWN | 35.09 | 0.00 | CONFIRMED |
| VS21-S13-15-F50 | 15 | 5 | 2.41 | UNKNOWN | 2.41 | 0.00 | CONFIRMED |
| VS21-S13 | 15 | 18 | 16.42 | UNKNOWN | 16.42 | 1.72 | CONFIRMED |
| VS31-S13-28-F60 | 28 | 4 | 36.74 | UNKNOWN | 36.74 | 0.00 | CONFIRMED |
| VS31-X32 | ? | 2 | 0.62 | UNKNOWN | 0.62 | 0.00 | CONFIRMED |
| VV01-X32 | 25 | 2 | 0.35 | UNKNOWN | 0.35 | 0.00 | CONFIRMED |
| VV01-X7-25-F60 | 25 | 2 | 0.99 | UNKNOWN | 0.99 | 0.74 | CONFIRMED |
| VV01-X7-32-F60 | 32 | 2 | 0.70 | UNKNOWN | 0.70 | 0.00 | CONFIRMED |
| VV01-X7-40-F60 | 40 | 1 | 16.99 | UNKNOWN | 16.99 | 0.00 | CONFIRMED |
| VVC01-X7-20 | 20 | 4 | 7.11 | UNKNOWN | 7.11 | 0.29 | CONFIRMED |
| VVC01-X7-32 | 32 | 1 | 17.32 | UNKNOWN | 17.32 | 0.00 | CONFIRMED |

Totals: confirmed horizontal 178.38 m, ambiguous 6.07 m, unowned pipe geometry 382.70 m

## Unresolved
- unknown_glyph: 98
- missing_dn: 41
- missing_leader: 39
- ambiguous_pipe_attachment: 23
- missing_pipe_attachment: 42
- branch_conflict: 5
- unowned_geometry: 12

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
