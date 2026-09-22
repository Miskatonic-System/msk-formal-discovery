"""Assemble the committed artifact package for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A.

  python -m msk_formal_discovery.topological_galois.bridge_finalize          rebuild cell-results / adjudication / result / hostile controls
                                                                             from the SAVED provider log (no new Maxima run) and validate
  python -m msk_formal_discovery.topological_galois.bridge_finalize --check  validate only
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from . import bridge_experiment as bx
from . import bridge_runner as br
from . import bridge_validate as bv

BASE = bx.EXPERIMENT_DIR
WO = bx.WORK_ORDER


def dump(name: str, obj) -> None:
    (BASE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def build() -> dict:
    pre = json.loads((BASE / "preregistration.v0.1.json").read_text(encoding="utf-8"))
    sig = pre["source_signature"]["SOURCE_SIGNATURE"]
    res = br.reclassify_from_log(pre, BASE / "cells")
    for c in res["cells"]:
        c["SOURCE_SIGNATURE"] = sig
        c["claimed_inferences"] = []
    res["schema_version"] = "miskatonic.formal-discovery.hvb-cell-results.v0.1"
    res["work_order"] = WO
    res["provider_script"] = "cells/target_cells.mac"
    res["provider_log"] = "cells/target_cells.log"
    dump("cell-results.v0.1.json", res)

    adj = br.adjudicate(pre, res["cells"])
    adj["schema_version"] = "miskatonic.formal-discovery.hvb-adjudication.v0.1"
    adj["work_order"] = WO
    adj["BO1"] = {"status": "NOT_EXECUTED", "reason": "no exact target-monodromy tuple was constructed in this WO (Morales-Ruiz 1999, the Zariski-closure source, is UNAVAILABLE; no monodromy computation was attempted), so there is no target data against which to verify the frozen Hurwitz transport. The structural action B_3 -> Aut(F_3) stays qualified from 01A; STRUCTURAL_EQUIVARIANCE_SUPPORTED is NOT earned here."}
    adj["BO3"] = "UNKNOWN (not addressed; n = 3 only)"
    dump("adjudication.v0.1.json", adj)

    nonabelian = [c["cell"] for c in res["cells"] if c["ABELIAN_IDENTITY_COMPONENT"] == "FALSE"]
    abelian = [c["cell"] for c in res["cells"] if c["ABELIAN_IDENTITY_COMPONENT"] == "TRUE"]
    unresolved = [c["cell"] for c in res["cells"] if c["ABELIAN_IDENTITY_COMPONENT"] == "UNRESOLVED"]
    disposition = ("HAMILTONIAN_VARIATIONAL_BRIDGE_BO2_REFUTED_SOURCE_INSUFFICIENT" if adj["BO2"] == "REFUTED"
                   else "BO2_NOT_FALSIFIED_ON_FROZEN_N3_GRID" if adj["BO2"] == "NOT_FALSIFIED_ON_FROZEN_N3_GRID" else "TARGET_GALOIS_CLASSIFICATION_PARTIAL")
    result = {
        "schema_version": "miskatonic.formal-discovery.hvb-result.v0.1",
        "work_order": WO,
        "canonical_start": bx.FD_START, "mathematics_sha": bx.MATH_SHA, "candidate_freeze_digest": bx.CANDIDATE_FREEZE_DIGEST,
        "preregistration_commit": bv.PREREG_COMMIT,
        "disposition": disposition,
        "disposition_status": "PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW",
        "BO2": adj["BO2"], "disposition_component": adj["disposition_component"], "witness_pair": adj["witness_pair"],
        "cells_abelian_TRUE": abelian, "cells_nonabelian_FALSE": nonabelian, "cells_UNRESOLVED": unresolved,
        "TARGET_VARIATIONAL_GALOIS_PREDICATE_NONABELIAN_CELLS": nonabelian,
        "SOURCE_SIGNATURE": sig,
        "degrees_executed": [3],
        "BURAU_ROLE": "CONTROL_ONLY",
        "FTT": "NOT_REQUIRED", "MORALES_RAMIS": "NOT_APPLIED", "NONINTEGRABILITY_CLAIM": "NONE", "CHAOS_CLAIM": "NONE",
        "rho_tgt_used_as_evidence_about_G_diff": False,
        "SOURCE_DATA_SUFFICIENT": None,
        "claimed_inferences": [],
        "claim_ceiling": [
            "For the frozen family (n = 3, P_3 = q^3 - q - 1, E = -1) the predicate ABELIAN_IDENTITY_COMPONENT(G_diff) of the algebraic NVE takes both values TRUE and FALSE at cells with identical SOURCE_SIGNATURE; hence the predicate is NOT a function of the qualified source representation data (pi_perm, alpha, Hurwitz) alone. This is a statement about the frozen family and the frozen source package only.",
            "FALSE cells: G_diff = SL_2(C) (Kovacic case 4) on the authority of the qualified provider (Maxima kovacicODE, K-matrix 10/10) plus an independent sympy case-1 exclusion. TRUE cells: exact Picard-Vessiot arguments (RD / R2L / RU) with polynomial-reduction verification; the provider only supplied candidate solutions.",
            "No integrability, nonintegrability or chaos statement about H_3 is made. Morales-Ramis is not applied. TARGET_VARIATIONAL_GALOIS_PREDICATE = NONABELIAN is recorded for the FALSE cells and nothing more.",
            "Absence of a counterexample would not have established SOURCE_DATA_SUFFICIENT; presence of one establishes insufficiency on this family only.",
            "BO-1 not executed (no target monodromy data); BO-3 unknown; n = 4..6 not run.",
        ],
        "permanent": ["MONODROMY_GROUP != DIFFERENTIAL_GALOIS_GROUP (closure source unbound: no monodromy used)", "NONABELIAN_G0 != CHAOS", "NONABELIAN_G0 != AUTHORIZED_NONINTEGRABILITY_CLAIM",
                      "LIOUVILLIAN != ABELIAN_IDENTITY_COMPONENT (Kovacic case 1 alone leaves the non-abelian Borel group possible)", "NOT_FALSIFIED != SOURCE_DATA_SUFFICIENT", "SOURCE_GROUP_ACTION != TARGET_MONODROMY_REPRESENTATION"],
    }
    dump("result.v0.1.json", result)

    dump("hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-hostile-controls.v0.1", "work_order": WO, "all_rejected": None, "count": 0, "results": []})
    with tempfile.TemporaryDirectory() as tmp:
        hostile = bv.run_hostile(BASE, Path(tmp))
    dump("hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-hostile-controls.v0.1", "work_order": WO,
                                          "all_rejected": all(h["rejected"] for h in hostile), "count": len(hostile), "results": hostile})
    return result


def main() -> int:
    if "--check" not in sys.argv:
        r = build()
        print("disposition:", r["disposition"], "| BO2:", r["BO2"], "| witness:", r["witness_pair"])
    errors = bv.validate(BASE)
    if errors:
        print("FAILED:", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    h = json.loads((BASE / "hostile-controls.v0.1.json").read_text())
    print(f"PASS: package validates; hostile {sum(x['rejected'] for x in h['results'])}/{h['count']} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
