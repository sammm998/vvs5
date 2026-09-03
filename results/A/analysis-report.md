# Analysis report: DRAWING_A

## Status
- designations: 142 (with DN 123)
- actual CAD leaders: 195 (from designation blocks: 150)
- pipe attachments: verified 114, ambiguous 1, none 20
- physical pipes: 45
- scale: VERIFIED (scale_text_and_scale_bar_agree)
- reconciliation: VALID (raw 10782.459 pt = confirmed 10589.976 + ambiguous 165.723 + unowned 26.76)
- determinism: PASS
- contamination: PASS
- runtime: 53.2 s

## Quantities (confirmed only; ambiguous reported separately)
| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |
|---|---|---|---|---|---|---|---|
| KV1-X31 | 16 | 2 | 17.26 | UNKNOWN | 17.26 | 0.00 | CONFIRMED |
| KV2-X31 | 16 | 5 | 33.42 | UNKNOWN | 33.42 | 0.00 | CONFIRMED |
| S1-P2-110 | 110 | 1 | 10.28 | 0.09 | 10.37 | 0.00 | CONFIRMED |
| S1-P2 | 75 | 4 | 4.20 | UNKNOWN | 4.20 | 0.00 | CONFIRMED |
| S3-P2-160 | 160 | 1 | 16.99 | UNKNOWN | 16.99 | 0.00 | CONFIRMED |
| S3-R8-110 | 110 | 5 | 56.19 | 0.41 | 56.60 | 0.62 | CONFIRMED |
| S3-R8-160 | 160 | 1 | 15.62 | 0.15 | 15.77 | 1.05 | CONFIRMED |
| S3-R8 | 75 | 21 | 21.69 | 0.18 | 21.87 | 1.28 | CONFIRMED |
| VV1-X31 | 16 | 5 | 34.24 | UNKNOWN | 34.24 | 0.00 | CONFIRMED |

Totals: confirmed horizontal 209.89 m, ambiguous 2.95 m, unowned pipe geometry 0.48 m

## Unresolved
- unknown_glyph: 26
- missing_dn: 19
- missing_leader: 20
- missing_pipe_attachment: 20
- ambiguous_pipe_attachment: 1
- branch_conflict: 1
- unowned_geometry: 1

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
