# Analysis report: DRAWING_C

## Status
- designations: 45 (with DN 36)
- actual CAD leaders: 19 (from designation blocks: 14)
- pipe attachments: verified 17, ambiguous 0, none 9
- physical pipes: 21
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 8448.6 pt = confirmed 2633.247 + ambiguous 193.159 + unowned 5622.194)
- determinism: PASS
- contamination: PASS
- runtime: 36.9 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV01-X7-40-W40 | 40 | 3 | 14.90 | UNKNOWN | 14.90 | 0.00 | CONFIRMED |
| S01-P5-160 | 160 | 1 | 2.37 | UNKNOWN | 2.37 | 0.00 | CONFIRMED |
| VP01-S2-65-F80 | 65 | 5 | 18.52 | UNKNOWN | 18.52 | 0.00 | CONFIRMED |
| VS21-S13-15-F50 | 15 | 2 | 12.37 | 0.50 | 12.87 | 1.65 | CONFIRMED |
| VS21-S13 | 15 | 3 | 1.67 | UNKNOWN | 1.67 | 1.78 | CONFIRMED |
| VS31-S13-28-F60 | 28 | 6 | 13.66 | UNKNOWN | 13.66 | 0.00 | CONFIRMED |
| VS31-X32 | 25 | 1 | 0.43 | UNKNOWN | 0.43 | 0.00 | CONFIRMED |

Totals: confirmed horizontal 63.93 m, ambiguous 3.44 m, unowned pipe geometry 100.11 m

## Unresolved
- unknown_glyph: 65
- missing_dn: 9
- missing_leader: 19
- missing_pipe_attachment: 9
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
