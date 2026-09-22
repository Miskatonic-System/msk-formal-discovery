# WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A

Machine-readable package for the exact source-representation qualification of the frozen
Hamiltonian bridge candidate CAND-1. Narrative and tables: `docs/TOPOLOGICAL_GALOIS_SOURCE_REPRESENTATION_01A.md`.

| Deliverable | File |
|---|---|
| 1 protocol | docs (Sec.1) |
| 2 convention freeze | `convention-freeze.v0.1.json` |
| 3 `B_n -> S_n` certificates | `certificates/s1-permutation-quotient.v0.1.json`, `certificates/permutation-quotient-kernel-witness.v0.1.json` |
| 4 Artin certificates | `certificates/s2-artin-action.v0.1.json` |
| 5 Hurwitz certificates | `certificates/hurwitz-action.v0.1.json` |
| 6 Burau qualification matrix | `burau-qualification-matrix.v0.1.json`, `certificates/s3-burau.v0.1.json` |
| 7 target puncture / fundamental group | `target-domain-derivation.v0.1.json` |
| 8 source-target action diagram | `source-target-diagram.v0.1.json` |
| 9 dependency minimization | `dependency-determination.v0.1.json` |
| 10 hostile + positive controls | `hostile-controls.v0.1.json`, `qualification-result.v0.1.json#/positive_controls` |
| 11 remaining bridge obligation | `source-target-diagram.v0.1.json#/remaining_bridge_obligation` |
| 12 qualification result | `qualification-result.v0.1.json`, `source-representation-manifest.v0.1.json` |
| sources | `source-ledger.v0.1.json` |

Regenerate / check:

```bash
python -m msk_formal_discovery.topological_galois.runner --check     # ~5 s; REPLAYS the sympy target-domain derivation and every certificate; fails closed without sympy (R1)
python -m msk_formal_discovery.topological_galois.runner --write     # regenerates; needs sympy for the target domain
python -m pytest tests/test_topological_galois_source_representation_01a.py
```

Certificates use exact integer / rational arithmetic and freely reduced words; nothing is floating point.
