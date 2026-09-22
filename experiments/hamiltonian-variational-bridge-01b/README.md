# WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B

Lamé parameter map and minimal missing-information qualification, following the canonical BO-2 refutation (01A).
Narrative: `docs/HAMILTONIAN_VARIATIONAL_BRIDGE_01B.md`.

| Item | File |
|---|---|
| Phase A exact parameter map, Phase C decomposition, Phase D grid (committed at `752e897d` before any provider run) | `preregistration.v0.1.json` |
| Phase B custody | `source-ledger.v0.1.json` |
| provider outputs (same qualified provider as 01A, identity parity) | `cell-results.v0.1.json`, `cells/target_cells.{mac,log}` |
| Phase D adjudication (pooled with the canonical 01A cells) | `adjudication.v0.1.json` |
| result / claim ceiling | `result.v0.1.json` |
| hostile controls | `hostile-controls.v0.1.json` |

```bash
python -m msk_formal_discovery.topological_galois.bridge_01b_finalize --check
python -m pytest tests/test_hamiltonian_variational_bridge_01b.py
```
