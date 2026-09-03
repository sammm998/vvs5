# Analysis report: DRAWING_A

## Status
- designations: 143 (with DN 122)
- actual CAD leaders: 201 (from designation blocks: 147)
- pipe attachments: verified 103, ambiguous 0, none 25
- physical pipes: 37
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 10782.459 pt = confirmed 7498.154 + ambiguous 165.723 + unowned 3118.582)
- determinism: PASS
- contamination: PASS
- runtime: 50.9 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV1-X31 | 16 | 1 | 10.36 | UNKNOWN | 10.36 | 0.00 | CONFIRMED |
| KV2-X31 | 16 | 1 | 6.30 | UNKNOWN | 6.30 | 0.00 | CONFIRMED |
| S1-P2-110 | 110 | 1 | 8.71 | 0.04 | 8.75 | 0.00 | CONFIRMED |
| S1-P2 | 75 | 5 | 10.45 | UNKNOWN | 10.45 | 0.00 | CONFIRMED |
| S1-P2 | ? | 1 | 2.72 | UNKNOWN | 2.72 | 0.00 | CONFIRMED |
| S3-P2-160 | 160 | 1 | 16.99 | UNKNOWN | 16.99 | 0.00 | CONFIRMED |
| S3-R8-110 | 110 | 6 | 50.73 | 0.25 | 50.98 | 1.15 | CONFIRMED |
| S3-R8-160 | 160 | 1 | 11.14 | 0.09 | 11.23 | 0.53 | CONFIRMED |
| S3-R8-75 | 75 | 20 | 39.27 | 0.12 | 39.39 | 1.28 | CONFIRMED |

Totals: confirmed horizontal 156.66 m, ambiguous 2.95 m, unowned pipe geometry 55.53 m

## Unresolved
- unknown_glyph: 26
- missing_dn: 21
- missing_leader: 33
- missing_pipe_attachment: 25
- unowned_geometry: 4
- branch_conflict: 1

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
