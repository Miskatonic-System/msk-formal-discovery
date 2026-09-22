"""Qualification protocol for WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A.

Contents
  * CONVENTION_FREEZE      every convention the work order names, each bound to a source locator
  * OBJECT_REGISTRY        the groups and maps in play, typed so that relabels are detectable
  * gate(claim)            typed hygiene gate: returns the set of rejection codes for one claim record
  * HOSTILE_CLAIMS         the sixteen hostile fixtures the work order requires
  * positive_controls()    PC1..PC6, each executed rather than asserted
  * dependency_determination()
  * build_artifacts()/validate()  writes and re-checks the machine-readable package

The gate is not a theorem prover. It checks that a claim is typed, sourced and inside the
frozen conventions; truth rests on the certificates in braid_source and target_domain.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from . import braid_source as bs

WORK_ORDER = "WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A"
REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = REPO_ROOT / "experiments" / "topological-galois-source-representation-01a"

MATH_SHA = "2337c7d744f176274997374a7d4057c7272f715d"
FD_SHA = "60b92dcb3069fe8312ee8901860f24233df1562f"
CANDIDATE_FREEZE_DIGEST = "889cc252226d801491a83bdd594e366fffc5a8bd1ef9379f5088bf9f65d78425"
RECONSTRUCTION_DIGEST = "5dbaab30927ed76acc6cb5ca2e36761e0f624ed1ef57f932c041e7e6eb9cc0cb"
BB = "src-tg-birman-brendle-2005"
BMP = "src-hmc-brendle-margalit-putman-2015"
DEGREES = (3, 4, 5, 6)
FROZEN_T = -1

CONVENTION_FREEZE: Dict[str, Dict[str, str]] = {
    "braid_multiplication_order": {"value": "juxtaposition: the word X Y is the braid X followed by the braid Y; words are read LEFT TO RIGHT", "source": f"{BB} Sec.1 (Fig.1: 'their product XY'; 'Multiplication of braids is by juxtaposition')"},
    "sigma_i_orientation": {"value": "sigma_i is the elementary braid of BB Fig.2(i) exchanging strands i and i+1; its orientation is FIXED relative to the free-group action by eq.(20): sigma_i x_i sigma_i^{-1} = x_{i+1}", "source": f"{BB} Sec.1.2, eq.(2); Sec.4.7 eq.(20)"},
    "free_group_generators_x_i": {"value": "F_n = pi_1(D_n, d_0), D_n the n-punctured disk with punctures q_1..q_n; x_i is the loop based at d_0 on the boundary travelling COUNTERCLOCKWISE about q_i", "source": f"{BB} Sec.4.4"},
    "left_vs_right_action": {"value": "LEFT action alpha: B_n -> Aut(F_n), alpha(beta)(x) = beta x beta^{-1} in F_n x| B_n; alpha(XY) = alpha(X) o alpha(Y), so for a word the RIGHTMOST letter acts first", "source": f"{BB} Sec.4.7 eq.(19),(20); left-action law verified in certificate S2 (left_action_verified_on_probe)"},
    "function_composition_order": {"value": "(f o g)(x) = f(g(x)); Endo.compose(self, other) = self o other, other applied first", "source": "freegroup.Endo.compose (local definition)"},
    "hurwitz_action_convention": {"value": "LEFT action on Hom(F_n, G): (beta . rho) = rho o alpha(beta^{-1}). Closed form for sigma_i: (M_i, M_{i+1}) -> (M_i M_{i+1} M_i^{-1}, M_i). The variant rho o alpha(beta) is a RIGHT action with closed form (M_i, M_{i+1}) -> (M_{i+1}, M_{i+1}^{-1} M_i M_{i+1}); it is recorded and is NOT the frozen convention", "source": "DERIVED from the frozen Artin action; certificate HURWITZ (closed_form checks); no separate literature source is claimed"},
    "puncture_ordering": {"value": "punctures q_1..q_n of D_n numbered so that sigma_i exchanges q_i and q_{i+1}; target roots r_1..r_n of f_{a,E} carry the same numbering (any reordering is an element of S_n and is recorded, not assumed)", "source": f"{BB} Sec.1 (strands numbered 1..n), Sec.4.4; target-domain-derivation.v0.1.json#/degrees/*/pi_1/ordering"},
    "loop_orientation": {"value": "counterclockwise", "source": f"{BB} Sec.4.4"},
    "B_n_to_S_n_quotient_convention": {"value": "pi_perm(sigma_i) = s_i = (i i+1); permutations are tuples p with p[k] = image of k and are composed LEFT TO RIGHT, (p*q)(k) = q(p(k)), so pi_perm is a homomorphism from the juxtaposition product", "source": f"{BB} Sec.1.1 eq.(1), Sec.4.1; certificate S1"},
    "reduced_vs_unreduced_burau": {"value": "UNREDUCED: sigma_i -> I_{i-1} (+) [[1-t, t],[1, 0]] (+) I_{n-i-1} in GL_n. REDUCED: sigma_i -> I_{i-2} (+) [[1,-t,0],[0,-t,0],[0,-1,1]] (+) I_{n-i-2} in GL_{n-1}, the -t in the (i,i) spot. The two are never interchanged; dimensions n and n-1", "source": f"{BB} Sec.4.2 p.46 (signs read from the rendered PDF page, not from a text extraction)"},
    "burau_specialization_value": {"value": "t = -1 (the specialization used by 00A check S1 and by BMP's beta_n); t = 2 is a CONTROL specialization only; t = 1 recovers the permutation representation", "source": f"{BMP} Sec.1 (Burau at t = -1); {BB} Sec.4.2 (t = 1)"},
    "matrices_acting_on_rows_vs_columns": {"value": "matrices act on COLUMN vectors from the LEFT; beta(XY) = beta(X) beta(Y). The row-vector (right) action on the sum-zero hyperplane is used only as a decomposition control and is transposed before comparison", "source": "certificate S3 (matrix_action_convention, decomposition)"},
    "conjugation_convention": {"value": "conj(a, b) = a b a^{-1}; the Artin action is conjugation of x_j by sigma_i in F_n x| B_n, sigma_i x_j sigma_i^{-1}", "source": f"{BB} Sec.4.7 eq.(20); freegroup.conj"},
    "word_equality": {"value": "two braid words are compared only through their images (in S_n, Aut(F_n), or GL); two free-group words are equal iff their free reductions coincide", "source": "freegroup.reduce_word (local definition)"},
}

OBJECT_REGISTRY: Dict[str, Dict[str, str]] = {
    "B_n": {"kind": "GROUP", "definition": "pi_1(C_{0,n}, base) of the unordered configuration space of n points in C (BB Sec.1.1); source-side parameter loops", "role": "SOURCE_GROUP"},
    "F_n": {"kind": "GROUP", "definition": "pi_1(P^1_q minus (n finite roots of f_{a,E} + infinity)) = pi_1(D_n, d_0), free on x_1..x_n", "role": "TARGET_FUNDAMENTAL_GROUP"},
    "S_n": {"kind": "GROUP", "definition": "symmetric group on the n strands / punctures", "role": "QUOTIENT"},
    "pi_perm": {"kind": "HOMOMORPHISM", "domain": "B_n", "codomain": "S_n", "faithful": "NO (kernel = P_n, witnessed by sigma_1^2)", "role": "S1"},
    "alpha": {"kind": "GROUP_ACTION", "domain": "B_n", "codomain": "Aut(F_n)", "role": "S2"},
    "beta_n": {"kind": "LINEAR_REPRESENTATION", "domain": "B_n", "codomain": "GL_{n-1}(Z) (reduced) / GL_n(Z) (unreduced) at t = -1", "role": "S3"},
    "rho_tgt": {"kind": "REPRESENTATION_VALUE", "domain": "F_n", "codomain": "GL_2(C)", "role": "TARGET_MONODROMY (not computed in this WO)", "monodromy_kind": "MK-VARIATIONAL"},
    "G_diff": {"kind": "ALGEBRAIC_GROUP", "definition": "differential Galois group of the algebraic NVE over C(q); contains the Zariski closure of the image of rho_tgt (Fuchsian case, source IDENTIFIED only in 00A)", "role": "TARGET_PREDICATE_CARRIER (not computed)"},
}

PERMANENT = [
    "B_n != F_n",
    "GROUP_ACTION != REPRESENTATION_VALUE",
    "SOURCE_GROUP_ACTION != TARGET_MONODROMY_REPRESENTATION",
    "PERMUTATION_QUOTIENT != FAITHFUL_BRAID_REPRESENTATION",
    "REDUCED_BURAU != UNREDUCED_BURAU",
    "REPRESENTATION != ITS_DUAL (for even n the reduced Burau at t=-1 and its dual are inequivalent; only the dual carries an invariant alternating form)",
    "LOCAL_ALTERNATING_FORM != SOURCED_SYMPLECTIC_THEOREM",
    "ODD_DEGREE_SOURCE_STATEMENT != EVEN_DEGREE_STATEMENT",
    "SINGULAR_POLYNOMIAL = E - P_n, NOT P_n",
    "INFINITY_IS_A_PUNCTURE",
    "TARGET_MONODROMY_GROUP != DIFFERENTIAL_GALOIS_GROUP (without Zariski-closure scope)",
    "SAME_WORD_MONODROMY != BRIDGE_EVIDENCE",
    "INTERESTING_STRUCTURE != NECESSARY_STRUCTURE",
]


# ---------------------------------------------------------------------------
# the typed gate
# ---------------------------------------------------------------------------

FROZEN_ARTIN_GENERATOR = {n: {i: bs.artin_generator(n, i, 1).to_json() for i in range(1, n)} for n in DEGREES}
FROZEN_ARTIN_INVERSE = {n: {i: bs.artin_generator(n, i, -1).to_json() for i in range(1, n)} for n in DEGREES}
BOUND_EVEN_DEGREE_SOURCES: set = set()          # no source binds the even-degree symplectic statement in this WO
ODD_DEGREE_SOURCE_SCOPE = {"source": BMP, "scope": "n = 2g+1 only"}


def gate(claim: Dict[str, Any]) -> set:
    """Return rejection codes for a claim record. Empty set = admitted. Keys on typed fields only."""
    codes: set = set()
    ct = claim.get("claim_type")

    if ct == "GROUP_IDENTIFICATION":
        a, b = claim["identify"]
        if a != b and {a, b} <= set(OBJECT_REGISTRY) and OBJECT_REGISTRY[a]["role"] != OBJECT_REGISTRY[b]["role"]:
            codes.add(f"DISTINCT_OBJECTS:{a}!={b}")
    elif ct == "FAITHFULNESS":
        if claim["map"] == "pi_perm" and claim.get("faithful") is True:
            w = bs.permutation_quotient_kernel_witness(claim.get("n", 3))
            if w["pi_perm_image_is_identity"] and not w["artin_image_is_identity"]:
                codes.add("NONTRIVIAL_KERNEL_WITNESS:sigma_1^2")
    elif ct == "ARTIN_GENERATOR_ACTION":
        n, i = claim["n"], claim["i"]
        if claim["labelled_as"] == "alpha(sigma_i)" and claim["images"] != FROZEN_ARTIN_GENERATOR[n][i]:
            if claim["images"] == FROZEN_ARTIN_INVERSE[n][i]:
                codes.add("ACTION_HANDEDNESS_REVERSED:images_equal_alpha(sigma_i^-1)")
            else:
                codes.add("ACTION_MISMATCH_WITH_FREEZE")
    elif ct == "ACTION_SIDE":
        if claim["side"] != "LEFT" or claim["letter_order"] != "RIGHTMOST_FIRST":
            codes.add("CONVENTION_DRIFT:left_vs_right_action")
    elif ct == "WORD_ORDER":
        if claim["order"] != "LEFT_TO_RIGHT":
            codes.add("CONVENTION_DRIFT:braid_multiplication_order")
        # exact witness: the two orders give different automorphisms on sigma_1 sigma_2
        n = claim.get("n", 3)
        fwd = bs.artin_of_word(n, bs.bmul(bs.sigma(1), bs.sigma(2)))
        rev = bs.artin_of_word(n, bs.bmul(bs.sigma(2), bs.sigma(1)))
        if fwd == rev:
            codes.add("WITNESS_FAILED:orders_indistinguishable")
    elif ct == "HURWITZ_TUPLE_MOVE":
        i = claim["i"]
        tup = bs.frozen_tuples()["n4_involutions_00A"]
        if claim["labelled_as"] == "frozen_left_action" and claim["move"] == "(M_i+1, M_i+1^-1 M_i M_i+1)":
            if bs.tuple_move_right_variant(i, tup) != bs.tuple_move_left(i, tup):
                codes.add("TUPLE_CONVENTION_MISMATCH:move_is_the_right_variant")
    elif ct == "BURAU_VARIANT":
        n = claim["n"]
        expected = n - 1 if claim["variant"] == "reduced" else n
        if claim["dimension"] != expected:
            codes.add("BURAU_VARIANT_CONFLATION:dimension")
    elif ct == "BURAU_SPECIALIZATION":
        if claim["labelled_as"] == "frozen_specialization" and claim["t"] != FROZEN_T:
            codes.add(f"SPECIALIZATION_DRIFT:t={claim['t']}!={FROZEN_T}")
    elif ct == "AUTHORITY_ASSIGNMENT":
        n, auth = claim["n"], claim["authority"]
        if auth == "EXTERNAL_THEOREM_SCOPED":
            src = claim.get("source")
            if n % 2 == 0:
                if src is None or src not in BOUND_EVEN_DEGREE_SOURCES:
                    codes.add("AUTHORITY_NOT_EARNED:no_bound_even_degree_source")
                if src == ODD_DEGREE_SOURCE_SCOPE["source"]:
                    codes.add("SCOPE_EXTRAPOLATION:odd_degree_source_applied_to_even_degree")
            elif src != ODD_DEGREE_SOURCE_SCOPE["source"]:
                codes.add("AUTHORITY_NOT_EARNED:no_bound_source")
    elif ct == "PUNCTURE_ACCOUNTING":
        n = claim["n"]
        finite = claim["finite_punctures"]
        if not claim.get("includes_infinity", False):
            codes.add(f"PUNCTURE_ACCOUNTING_INCOMPLETE:infinity_omitted(rank_would_be_{finite - 1}_not_{claim['claimed_rank']})")
        elif claim["claimed_rank"] != finite:
            codes.add("RANK_MISMATCH")
    elif ct == "SINGULAR_POLYNOMIAL":
        if claim["polynomial"] == "P_n" and not claim.get("energy_frozen_to_zero", False):
            codes.add("SINGULAR_POLYNOMIAL_MISMATCH:P_n_used_where_E-P_n_required")
    elif ct == "KIND_ASSIGNMENT":
        obj = claim["object"]
        if OBJECT_REGISTRY.get(obj, {}).get("kind") == "GROUP_ACTION" and claim.get("monodromy_kind") is not None:
            codes.add("GROUP_ACTION_RELABELED_AS_REPRESENTATION_VALUE")
    elif ct == "GALOIS_ASSIGNMENT":
        if claim["asserted_as"] == "G_diff" and not claim.get("zariski_closure_scope"):
            codes.add("GALOIS_SCOPE_MISSING:no_Zariski_closure_or_theorem_scope")
    elif ct == "PROVIDER_IMPORT":
        if claim["provider"] == "msk-ftt-nhe" and not claim.get("ftt_specific_operation", False):
            codes.add("FTT_NOT_REQUIRED_VIOLATION")
    elif ct == "EVIDENCE":
        if "SHARED_TERMINOLOGY" in claim.get("basis", []) and not ({"SOURCE_THEOREM", "LOCAL_DERIVED_CHECK"} & set(claim.get("basis", []))):
            codes.add("SHARED_TERMINOLOGY_NOT_EVIDENCE")
    else:
        codes.add(f"UNKNOWN_CLAIM_TYPE:{ct}")
    return codes


HOSTILE_CLAIMS: List[Dict[str, Any]] = [
    {"id": "H01", "pattern": "B_n relabeled F_n", "claim": {"claim_type": "GROUP_IDENTIFICATION", "identify": ["B_n", "F_n"]}, "expected": ["DISTINCT_OBJECTS:B_n!=F_n"]},
    {"id": "H02", "pattern": "B_n -> S_n quotient relabeled faithful braid representation", "claim": {"claim_type": "FAITHFULNESS", "map": "pi_perm", "faithful": True, "n": 3}, "expected": ["NONTRIVIAL_KERNEL_WITNESS:sigma_1^2"]},
    {"id": "H03", "pattern": "Artin action direction reversed", "claim": {"claim_type": "ARTIN_GENERATOR_ACTION", "n": 3, "i": 1, "labelled_as": "alpha(sigma_i)", "images": {"x1": "x1 x2 x1^-1", "x2": "x1", "x3": "x3"}}, "expected": ["ACTION_HANDEDNESS_REVERSED:images_equal_alpha(sigma_i^-1)"]},
    {"id": "H04", "pattern": "left/right action convention switched after freeze", "claim": {"claim_type": "ACTION_SIDE", "side": "RIGHT", "letter_order": "LEFTMOST_FIRST"}, "expected": ["CONVENTION_DRIFT:left_vs_right_action"]},
    {"id": "H05", "pattern": "word-composition order reversed", "claim": {"claim_type": "WORD_ORDER", "order": "RIGHT_TO_LEFT", "n": 3}, "expected": ["CONVENTION_DRIFT:braid_multiplication_order"]},
    {"id": "H06", "pattern": "Hurwitz tuple convention silently changed", "claim": {"claim_type": "HURWITZ_TUPLE_MOVE", "i": 1, "labelled_as": "frozen_left_action", "move": "(M_i+1, M_i+1^-1 M_i M_i+1)"}, "expected": ["TUPLE_CONVENTION_MISMATCH:move_is_the_right_variant"]},
    {"id": "H07", "pattern": "reduced and unreduced Burau conflated", "claim": {"claim_type": "BURAU_VARIANT", "n": 5, "variant": "reduced", "dimension": 5}, "expected": ["BURAU_VARIANT_CONFLATION:dimension"]},
    {"id": "H08", "pattern": "Burau specialization silently changed", "claim": {"claim_type": "BURAU_SPECIALIZATION", "labelled_as": "frozen_specialization", "t": 2}, "expected": ["SPECIALIZATION_DRIFT:t=2!=-1"]},
    {"id": "H09", "pattern": "local n=4/n=6 alternating-form check relabeled theorem authority", "claim": {"claim_type": "AUTHORITY_ASSIGNMENT", "n": 4, "authority": "EXTERNAL_THEOREM_SCOPED", "source": None}, "expected": ["AUTHORITY_NOT_EARNED:no_bound_even_degree_source"]},
    {"id": "H10", "pattern": "odd-degree source theorem extrapolated to even degree", "claim": {"claim_type": "AUTHORITY_ASSIGNMENT", "n": 6, "authority": "EXTERNAL_THEOREM_SCOPED", "source": BMP}, "expected": ["AUTHORITY_NOT_EARNED:no_bound_even_degree_source", "SCOPE_EXTRAPOLATION:odd_degree_source_applied_to_even_degree"]},
    {"id": "H11", "pattern": "infinity omitted from target puncture accounting", "claim": {"claim_type": "PUNCTURE_ACCOUNTING", "n": 5, "finite_punctures": 5, "includes_infinity": False, "claimed_rank": 5}, "expected": ["PUNCTURE_ACCOUNTING_INCOMPLETE:infinity_omitted(rank_would_be_4_not_5)"]},
    {"id": "H12", "pattern": "roots of P_n substituted for roots of E-P_n", "claim": {"claim_type": "SINGULAR_POLYNOMIAL", "polynomial": "P_n", "energy_frozen_to_zero": False}, "expected": ["SINGULAR_POLYNOMIAL_MISMATCH:P_n_used_where_E-P_n_required"]},
    {"id": "H13", "pattern": "source group action relabeled target monodromy", "claim": {"claim_type": "KIND_ASSIGNMENT", "object": "alpha", "monodromy_kind": "MK-VARIATIONAL"}, "expected": ["GROUP_ACTION_RELABELED_AS_REPRESENTATION_VALUE"]},
    {"id": "H14", "pattern": "target monodromy relabeled differential Galois group without Zariski-closure / theorem scope", "claim": {"claim_type": "GALOIS_ASSIGNMENT", "object": "image of rho_tgt", "asserted_as": "G_diff", "zariski_closure_scope": None}, "expected": ["GALOIS_SCOPE_MISSING:no_Zariski_closure_or_theorem_scope"]},
    {"id": "H15", "pattern": "FTT artifact imported despite FTT_ROLE=NOT_REQUIRED", "claim": {"claim_type": "PROVIDER_IMPORT", "provider": "msk-ftt-nhe", "object": "YANG_LEE_B6_REPRESENTATION", "ftt_specific_operation": False}, "expected": ["FTT_NOT_REQUIRED_VIOLATION"]},
    {"id": "H16", "pattern": "same word 'monodromy' accepted as bridge evidence", "claim": {"claim_type": "EVIDENCE", "basis": ["SHARED_TERMINOLOGY"]}, "expected": ["SHARED_TERMINOLOGY_NOT_EVIDENCE"]},
]

REPAIRED_CLAIMS: List[Dict[str, Any]] = [   # the same patterns, corrected: the gate must admit these (it keys on fields, not on names)
    {"id": "R03", "claim": {"claim_type": "ARTIN_GENERATOR_ACTION", "n": 3, "i": 1, "labelled_as": "alpha(sigma_i)", "images": FROZEN_ARTIN_GENERATOR[3][1]}},
    {"id": "R04", "claim": {"claim_type": "ACTION_SIDE", "side": "LEFT", "letter_order": "RIGHTMOST_FIRST"}},
    {"id": "R07", "claim": {"claim_type": "BURAU_VARIANT", "n": 5, "variant": "reduced", "dimension": 4}},
    {"id": "R09", "claim": {"claim_type": "AUTHORITY_ASSIGNMENT", "n": 5, "authority": "EXTERNAL_THEOREM_SCOPED", "source": BMP}},
    {"id": "R11", "claim": {"claim_type": "PUNCTURE_ACCOUNTING", "n": 5, "finite_punctures": 5, "includes_infinity": True, "claimed_rank": 5}},
    {"id": "R12", "claim": {"claim_type": "SINGULAR_POLYNOMIAL", "polynomial": "E - P_n"}},
    {"id": "R14", "claim": {"claim_type": "GALOIS_ASSIGNMENT", "object": "image of rho_tgt", "asserted_as": "G_diff", "zariski_closure_scope": "Fuchsian case: Zariski closure of the monodromy group; source to be bound (00A P2)"}},
]


# ---------------------------------------------------------------------------
# positive controls
# ---------------------------------------------------------------------------

def positive_controls(certs: Dict[str, Any]) -> List[Dict[str, Any]]:
    s2_3 = certs["S2"]["3"]
    hz = certs["HURWITZ"]["n4_involutions_00A"]
    s3 = certs["S3"]
    # PC6: 00A S2 coded the tuple move (t_i, t_{i+1}) -> (t_i t_{i+1} t_i^{-1}, t_i); compare with the frozen closed form exactly
    tup = bs.frozen_tuples()["n4_involutions_00A"]

    def hurwitz_00a(tp, i):            # verbatim shape of the 00A check S2 move (0-indexed i)
        tp = list(tp)
        tp[i], tp[i + 1] = bs.mmul(bs.mmul(tp[i], tp[i + 1]), bs.minv(tp[i])), tp[i]
        return tuple(tp)

    pc6_hurwitz = all(hurwitz_00a(tup, i - 1) == bs.tuple_move_left(i, tup) == bs.hurwitz_left(4, bs.sigma(i), tup) for i in range(1, 4))
    pc6_burau = {n: s3[str(n)]["comparison_with_00A_S1_matrices"] for n in DEGREES}
    pc6_burau_odd_equiv = all(pc6_burau[n]["00A_vs_BB_reduced_t=-1"]["equivalent"]["intertwiner"] is not None for n in (3, 5))
    pc6_burau_even_dual = all(pc6_burau[n]["00A_vs_BB_reduced_t=-1"]["equivalent_to_dual_(inverse_transpose)"]["intertwiner"] is not None
                              and pc6_burau[n]["00A_vs_BB_reduced_t=-1"]["equivalent"]["intertwiner"] is None for n in (4, 6))
    return [
        {"id": "PC1", "control": "exact B_3 -> S_3 quotient", "result": certs["S1"]["3"]["result"], "detail": f"image size {certs['S1']['3']['image_size']} = 3!, relations and squares verified"},
        {"id": "PC2", "control": "exact Artin B_3 action on F_3", "result": s2_3["result"], "detail": s2_3["generator_action"]},
        {"id": "PC3", "control": "braid relation under Artin action", "result": "PASS" if all(r["holds"] for n in DEGREES for r in certs["S2"][str(n)]["relations"]) else "FAIL", "detail": "all relations of B_n hold in Aut(F_n) for n = 3..6"},
        {"id": "PC4", "control": "Artin action induces the expected permutation", "result": "PASS" if all(v["agrees_with_S1"] for n in DEGREES for v in certs["S2"][str(n)]["induced_permutation"].values()) else "FAIL", "detail": "abelianization of alpha(sigma_i) is the permutation matrix of pi_perm(sigma_i) for n = 3..6"},
        {"id": "PC5", "control": "exact Hurwitz transport on an explicit tuple", "result": hz["result"], "detail": "n=4 involution tuple: relations, closed form, left-action law, inverse, ordered product, relabel, nontriviality"},
        {"id": "PC6", "control": "source package reproduces accepted 00A S1/S2 controls where semantics overlap",
         "result": "PASS" if (pc6_hurwitz and pc6_burau_odd_equiv and pc6_burau_even_dual) else "FAIL",
         "detail": {
             "00A_S2_tuple_move_equals_frozen_left_Hurwitz_move": pc6_hurwitz,
             "00A_S1_Burau_matrices_vs_BB_reduced_t=-1": {"odd_n_(3,5)": "EQUIVALENT (explicit intertwiner); self-dual", "even_n_(4,6)": "EQUIVALENT TO THE DUAL (inverse-transpose; intertwiner = identity) and NOT equivalent to BB reduced itself"},
             "consequence": "00A's even-n 'invariant alternating form of rank 2g' is a property of the dual convention only; BB reduced at t=-1 has NO invariant alternating form for n = 4, 6. For odd n the two conventions coincide.",
         }},
    ]


# ---------------------------------------------------------------------------
# dependency minimization
# ---------------------------------------------------------------------------

def dependency_determination(certs: Dict[str, Any]) -> Dict[str, Any]:
    even_forms = {n: certs["S3"][str(n)]["invariant_alternating_forms_t=-1"] for n in (4, 6)}
    return {
        "rule": "an object is LOAD_BEARING iff at least one frozen bridge obligation (BO-1, BO-2, BO-3 of CAND-1) cannot be STATED without it; INTERESTING_STRUCTURE != NECESSARY_STRUCTURE",
        "objects": {
            "S1_pi_perm": {"classification": "LOAD_BEARING", "used_by": ["BO-1 (relabelling of roots / of conjugacy classes in a monodromy tuple under a parameter braid)", "BO-3 (the degree-ladder source invariants live on S_n)"],
                            "certificate": "certificates/s1-permutation-quotient.v0.1.json"},
            "S2_artin_hurwitz": {"classification": "LOAD_BEARING", "used_by": ["BO-1 (the B_n-equivariant monodromy-data map is DEFINED through alpha: (beta . rho) = rho o alpha(beta^{-1}))", "BO-2, BO-3 (transport of tuples is the only proposed structural relation)"],
                                  "certificate": "certificates/s2-artin-action.v0.1.json, certificates/hurwitz-action.v0.1.json"},
            "S3_burau": {"classification": "CONTROL_ONLY", "reason": "no bridge obligation mentions beta_n; BO-1..BO-3 are stated entirely with pi_perm and alpha. Retained as (i) the overlap control with 00A S1 and (ii) the source-side carrier of the odd-n symplectic reading (S4)", "certificate": "certificates/s3-burau.v0.1.json",
                         "removed_from_bridge_critical_path": True},
            "S4_symplectic_interpretation": {
                "odd_n_(3,5)": {"classification": "CONTROL_ONLY", "custody": f"{BMP} (BOUND, SHA-256 in the 00A ledger consumed by git blob 4cafe426d4b23b82a93b74d7c946d97bb95c0b41); statement scope n = 2g+1", "local_confirmation": "reduced Burau at t=-1 carries a unique nondegenerate invariant alternating form (rank n-1) for n = 3, 5"},
                "even_n_(4,6)": {"classification": "SOURCE_INSUFFICIENT", "status": "LOCAL_ALGEBRA_CONTROL_ONLY", "custody": "no source bound in this WO (none was sought: Burau is not load-bearing, and the work order forbids adding dependencies for symmetry)",
                                  "local_fact": {f"n={n}": {"BB_reduced": even_forms[n]["BB_reduced"], "BB_reduced_dual": even_forms[n]["BB_reduced_dual"]} for n in (4, 6)},
                                  "note": "the local rank-2g form exists only for the dual convention; this is why a local alternating form is not a theorem"},
            },
        },
        "minimal_package": {"LOAD_BEARING": ["B_n -> S_n permutation quotient (S1)", "Artin/Hurwitz action of B_n on F_n (S2)"], "CONTROL_ONLY": ["reduced/unreduced Burau at t = -1 (S3)", "odd-n symplectic reading (S4, BMP)"], "SOURCE_INSUFFICIENT": ["even-n symplectic reading (S4)"]},
        "BURAU_ROLE": "CONTROL_ONLY",
        "expected_dependency_hypothesis_of_the_work_order": "EARNED (not inherited): the hypothesis matched, and the even-n dual-convention finding is new evidence in its favour",
    }


# ---------------------------------------------------------------------------
# artifacts
# ---------------------------------------------------------------------------

def canonical_digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def build_certificates() -> Dict[str, Any]:
    return {
        "S1": {str(n): bs.s1_certificate(n) for n in DEGREES},
        "S2": {str(n): bs.s2_certificate(n) for n in DEGREES},
        "HURWITZ": {label: bs.hurwitz_certificate(label, tup) for label, tup in bs.frozen_tuples().items()},
        "S3": {str(n): bs.s3_certificate(n, FROZEN_T, 2) for n in DEGREES},
        "KERNEL_WITNESS": {str(n): bs.permutation_quotient_kernel_witness(n) for n in DEGREES},
    }


def hostile_results() -> List[Dict[str, Any]]:
    out = []
    for h in HOSTILE_CLAIMS:
        got = sorted(gate(h["claim"]))
        out.append({**h, "got": got, "rejected_for_exactly_the_stated_reasons": got == sorted(h["expected"])})
    for r in REPAIRED_CLAIMS:
        got = sorted(gate(r["claim"]))
        out.append({"id": r["id"], "pattern": "repaired counterpart (must be admitted)", "claim": r["claim"], "expected": [], "got": got, "rejected_for_exactly_the_stated_reasons": got == []})
    return out


def source_target_diagram() -> Dict[str, Any]:
    return {
        "source_side": {"B_n": "pi_1(UConf_n(C)) — parameter loops", "pi_perm: B_n -> S_n": "S1", "alpha: B_n -> Aut(F_n)": "S2"},
        "target_side": {"F_n": "pi_1(P^1_q minus (roots of f_{a,E} + infinity))", "rho_tgt: F_n -> GL_2(C)": "monodromy of the algebraic NVE (NOT computed here)", "G_diff": "Zariski closure scope required (NOT computed here)"},
        "only_allowed_structural_relation": "B_n acts on F_n through alpha; hence B_n acts on Hom(F_n, GL_2(C))/conj by (beta . [rho]) = [rho o alpha(beta^{-1})] — the frozen LEFT Hurwitz action, exact on tuples (certificate HURWITZ)",
        "what_it_does_NOT_establish": ["rho_src = rho_tgt", "B_n = F_n", "Burau = NVE monodromy", "source representation determines G_diff"],
        "diagram": "B_n --alpha--> Aut(F_n)      and separately      rho_tgt : F_n -> GL_2(C)      ;  B_n acts on Hom(F_n, GL_2(C))/conj",
        "remaining_bridge_obligation": {
            "BO-1_structural": "exhibit the parameter-braid -> monodromy-tuple transport as the map beta -> beta . [rho_tgt] and state its domain of validity (which parameter loops, which basepoint conventions). Expected TRUE; now STATABLE with S1 + S2 only.",
            "BO-2_predicate_transport": "decide whether 'G^0 abelian' is a function of (n, pi_perm data, alpha-orbit data) alone. Expected FALSE. Falsification design: fix (n, a, E) hence the root configuration and all source data; vary (mu, lambda); ask whether the predicate changes. Nothing on the source side sees (mu, lambda).",
            "BO-3_residual": "with the coupling class fixed, ask whether any degree-distinguishing source invariant constrains G. UNKNOWN.",
            "not_executed_here": ["Kovacic on CAND-1", "G_diff", "G^0 classification", "(mu, lambda) sweep", "Morales-Ramis", "integrability/chaos claims"],
        },
    }


def build_artifacts(target_domain: Dict[str, Any] | None = None) -> Dict[str, Any]:
    certs = build_certificates()
    pcs = positive_controls(certs)
    hostile = hostile_results()
    dep = dependency_determination(certs)
    cert_files = {
        "certificates/s1-permutation-quotient.v0.1.json": certs["S1"],
        "certificates/s2-artin-action.v0.1.json": certs["S2"],
        "certificates/hurwitz-action.v0.1.json": certs["HURWITZ"],
        "certificates/s3-burau.v0.1.json": certs["S3"],
        "certificates/permutation-quotient-kernel-witness.v0.1.json": certs["KERNEL_WITNESS"],
    }
    all_pass = (all(c["result"] == "PASS" for group in ("S1", "S2", "S3") for c in certs[group].values())
                and all(c["result"] == "PASS" for c in certs["HURWITZ"].values())
                and all(p["result"] == "PASS" for p in pcs) and all(h["rejected_for_exactly_the_stated_reasons"] for h in hostile)
                and (target_domain is None or target_domain["result"] == "PASS"))
    manifest = {
        "schema_version": "miskatonic.formal-discovery.tg-source-representation-manifest.v0.1",
        "work_order": WORK_ORDER,
        "gate0": {"mathematics_main": MATH_SHA, "formal_discovery_main": FD_SHA, "candidate_freeze_digest": CANDIDATE_FREEZE_DIGEST, "reconstruction_digest": RECONSTRUCTION_DIGEST,
                  "predecessor_blobs_at_mathematics_main": {"candidate-freeze.v0.1.json": "e0c5d4627dba5560ffc34740ac746c0fc632697d", "determination.v0.1.json": "a2098a65404dc0c1126661d9dd87f1cc35be6f10", "reconstruction-receipt.v0.1.json": "fff84ffc71b70b53c9a75b34ef24313c919e22ba", "sources.v0.1.json": "4cafe426d4b23b82a93b74d7c946d97bb95c0b41", "monodromy-kind-registry.v0.1.json": "2069e62bafe94a3faeb88fdd5ef1676431597976", "docs/HAMILTONIAN_MONODROMY_POSITIVE_CONTROLS.md": "a3f6fbca7dd297bf0a14d602148a8c9d8ec8e3bd"}},
        "degrees": list(DEGREES), "frozen_burau_specialization_t": FROZEN_T,
        "source_objects": {"S1": "pi_perm: B_n -> S_n", "S2": "alpha: B_n -> Aut(F_n) (Artin), with the derived Hurwitz action", "S3": "beta_n: reduced/unreduced Burau at t = -1", "S4": "odd-n symplectic reading (BMP), even-n local only"},
        "certificate_digests": {k: canonical_digest(v) for k, v in cert_files.items()},
        "target_domain_digest": canonical_digest(target_domain) if target_domain is not None else None,
        "result": "PASS" if all_pass else "FAIL",
    }
    qual = {
        "schema_version": "miskatonic.formal-discovery.tg-qualification-result.v0.1",
        "work_order": WORK_ORDER,
        "disposition": "TOPOLOGICAL_GALOIS_SOURCE_REPRESENTATION_QUALIFIED" if all_pass else "SOURCE_REPRESENTATION_PARTIAL",
        "disposition_status": "PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW",
        "minimal_package": dep["minimal_package"], "BURAU_ROLE": dep["BURAU_ROLE"],
        "positive_controls": pcs, "hostile_controls_all_rejected_as_stated": all(h["rejected_for_exactly_the_stated_reasons"] for h in hostile),
        "hostile_control_count": len(HOSTILE_CLAIMS), "repaired_counterparts_admitted": all(h["rejected_for_exactly_the_stated_reasons"] for h in hostile if h["expected"] == []),
        "permanent": PERMANENT,
        "authority": {"NEW_MATHEMATICAL_THEOREM": "NONE", "HAMILTONIAN_BRIDGE": "NOT_EXECUTED", "DIFFERENTIAL_GALOIS_GROUP": "NOT_COMPUTED", "MORALES_RAMIS": "NOT_AUTHORIZED", "FTT": "NOT_REQUIRED", "ONTO_EXP_007": "PARKED", "RULIOLOGY_EXECUTION": "NONE"},
        "not_done": ["Kovacic on CAND-1", "G_diff", "G^0 classification", "(mu, lambda) sweep", "Morales-Ramis", "integrability/nonintegrability claims", "chaos analysis", "mutation of miskatonic-mathematics sources/registry.v0.1.json", "any write to FTT/ONTO/Ruliology"],
        "manifest_digest": canonical_digest(manifest),
    }
    files = {
        "source-representation-manifest.v0.1.json": manifest,
        "convention-freeze.v0.1.json": {"schema_version": "miskatonic.formal-discovery.tg-convention-freeze.v0.1", "work_order": WORK_ORDER, "conventions": CONVENTION_FREEZE, "object_registry": OBJECT_REGISTRY, "permanent": PERMANENT},
        **cert_files,
        "burau-qualification-matrix.v0.1.json": {"schema_version": "miskatonic.formal-discovery.tg-burau-qualification-matrix.v0.1", "work_order": WORK_ORDER, "rows": {
            str(n): {"relations_hold_t=-1": certs["S3"][str(n)]["reduced"]["t=-1"]["relations_hold"], "relations_hold_t=2_control": certs["S3"][str(n)]["reduced"]["t=2"]["relations_hold"],
                     "invariant_alternating_forms": {k: v for k, v in certs["S3"][str(n)]["invariant_alternating_forms_t=-1"].items() if k != "note"},
                     "symplectic_interpretation": ("CONTROL_ONLY, source-bound (BMP, n = 2g+1)" if n % 2 else "LOCAL_ALGEBRA_CONTROL_ONLY (SOURCE_INSUFFICIENT); exists only for the dual convention"),
                     "00A_matrices_relation_to_BB_reduced": ("equivalent (self-dual)" if n % 2 else "equivalent to the DUAL only")} for n in DEGREES},
            "BURAU_ROLE": dep["BURAU_ROLE"]},
        "source-target-diagram.v0.1.json": source_target_diagram(),
        "dependency-determination.v0.1.json": {"schema_version": "miskatonic.formal-discovery.tg-dependency-determination.v0.1", "work_order": WORK_ORDER, **dep},
        "hostile-controls.v0.1.json": {"schema_version": "miskatonic.formal-discovery.tg-hostile-controls.v0.1", "work_order": WORK_ORDER, "results": hostile},
        "qualification-result.v0.1.json": qual,
    }
    if target_domain is not None:
        files["target-domain-derivation.v0.1.json"] = target_domain
    return files


def write_artifacts(files: Dict[str, Any], base: Path = EXPERIMENT_DIR) -> None:
    for name, obj in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_artifacts(base: Path = EXPERIMENT_DIR) -> Dict[str, Any]:
    out = {}
    for p in sorted(base.rglob("*.json")):
        out[str(p.relative_to(base))] = json.loads(p.read_text(encoding="utf-8"))
    return out


def recompute_target_domain():
    """Replay the target-domain derivation. Fails closed (returns None) when sympy is unavailable."""
    try:
        from . import target_domain
    except ImportError:
        return None
    return target_domain.derive_all()


def validate(base: Path = EXPERIMENT_DIR) -> List[str]:
    """Recompute EVERYTHING, including the sympy target-domain derivation, and compare with the committed artifacts.

    R1: the committed target-domain artifact is never trusted. It is replayed, compared by canonical
    digest, and every other artifact is rebuilt from the REPLAYED object, not from the committed one.
    """
    errors: List[str] = []
    committed = load_artifacts(base)
    td_committed = committed.get("target-domain-derivation.v0.1.json")
    td = recompute_target_domain()
    if td is None:
        errors.append("target-domain derivation could not be replayed (sympy unavailable): validation fails closed")
        return errors
    if td_committed is None:
        errors.append("target-domain-derivation.v0.1.json missing")
    elif canonical_digest(td) != canonical_digest(td_committed):
        errors.append("artifact target-domain-derivation.v0.1.json differs from a fresh replay of target_domain.derive_all()")
    fresh = build_artifacts(td)
    for name, obj in fresh.items():
        if name not in committed:
            errors.append(f"missing artifact {name}")
        elif canonical_digest(obj) != canonical_digest(committed[name]):
            errors.append(f"artifact {name} differs from a fresh recomputation")
    if td["result"] != "PASS":
        errors.append("target-domain derivation did not pass")
    else:
        for n, v in td["degrees"].items():
            if v["pi_1"]["rank"] != int(n) or v["puncture_count"] != int(n) + 1 or "E - P_n" not in v["singular_polynomial"]:
                errors.append(f"target domain n={n}: puncture accounting or singular polynomial wrong")
    q = committed.get("qualification-result.v0.1.json", {})
    if q.get("BURAU_ROLE") != "CONTROL_ONLY":
        errors.append("BURAU_ROLE must be CONTROL_ONLY per the dependency determination")
    if q.get("authority", {}).get("DIFFERENTIAL_GALOIS_GROUP") != "NOT_COMPUTED":
        errors.append("authority block altered")
    ledger = committed.get("source-ledger.v0.1.json")
    if ledger is None:
        errors.append("source ledger missing")
    else:
        ids = {s["source_id"]: s for s in ledger["sources"]}
        if BB not in ids or ids[BB]["status"] != "BOUND" or len(ids[BB]["content_digest"]) != 64:
            errors.append("Birman-Brendle must be BOUND with a SHA-256 digest")
        for cid in ("src-hmc-morales-ruiz-1999", "src-hmc-morales-ramis-2001"):
            if cid in ids and ids[cid]["status"] != "IDENTIFIED":
                errors.append(f"{cid} may not be promoted by this WO")
    return errors
