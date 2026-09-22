# WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C

Coupling-conditioned degree-ladder residual test (BO-3), following the canonical BO-2 refutation (01A) and the Lamé/accessory-parameter
result (01B). Narrative: `docs/HAMILTONIAN_VARIATIONAL_BRIDGE_01C.md`.

| Item | File |
|---|---|
| controlled family n = 3..6, source degree/background signatures, four coupling lanes, consumed n = 3 anchors, 12 new cells (committed before any provider run) | `preregistration.v0.1.json` |
| custody (additive; Lamé sources N3_ONLY; degree-ladder facts labels only) | `source-ledger.v0.1.json` |
| provider outputs, one script and log per (cell, form) | `cell-results.v0.1.json`, `cells/<cell>_{orig,red}.{mac,log}` |
| BO-3 adjudication: per-lane TARGET_SEQUENCE, transitions, falsifiers | `adjudication.v0.1.json` |
| result / claim ceiling | `result.v0.1.json` |
| hostile controls | `hostile-controls.v0.1.json` |

```bash
python -m msk_formal_discovery.topological_galois.bridge_01c_finalize --check
python -m pytest tests/test_hamiltonian_variational_bridge_01c.py
```
