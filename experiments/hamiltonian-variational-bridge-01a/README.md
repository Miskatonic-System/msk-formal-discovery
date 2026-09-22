# WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A

First execution of the frozen CAND-1 bridge obligation BO-2 (fixed source, varied coupling). Narrative and tables:
`docs/HAMILTONIAN_VARIATIONAL_BRIDGE_01A.md`.

| Return item | File |
|---|---|
| canonical starting SHA, digests | `result.v0.1.json`, `preregistration.v0.1.json#/gate0` |
| source custody table | `source-ledger.v0.1.json` |
| provider qualification (K-matrix, digests) | `provider-qualification.v0.1.json`, `provider/k_controls.{mac,log}` |
| preregistered frozen n=3 member grid, SOURCE_SIGNATURE, each exact target ODE | `preregistration.v0.1.json` (committed at `e22dd8cf` before any Galois run) |
| provider/certificate output per cell, independent predicate checks | `cell-results.v0.1.json`, `cells/target_cells.{mac,log}` |
| BO-1 / BO-2 / BO-3 adjudication | `adjudication.v0.1.json` |
| hostile results | `hostile-controls.v0.1.json` |
| limitations, claim ceiling | `result.v0.1.json#/claim_ceiling`, docs |

Replay / check (no Maxima needed; provider outputs are digest-bound logs):

```bash
python -m msk_formal_discovery.topological_galois.bridge_finalize --check
python -m pytest tests/test_hamiltonian_variational_bridge_01a.py
```

Re-running the provider needs user-level nix (`nix shell nixpkgs#maxima`): `bridge_runner.provider_qualification`, `bridge_runner.run_cells`.
