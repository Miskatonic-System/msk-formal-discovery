# REGB Refined: Representation–Information Accessibility Conjecture

**Status:** CONJECTURE_SEED  
**Origin:** Representation-Entanglement Geometric Barrier brainstorm  
**Formal authority:** NONE

## 1. Canonical refinement

The original REGB brainstorm proposed a direct chain:

`large non-Abelian irreps -> intra-irrep entanglement -> negative geometry -> exponential circuit depth -> outside BQP`.

That chain is **not canonical**. Known results already require several separations:

- high-dimensional irreps do not imply an inefficient quantum Fourier transform;
- non-Abelian groups can admit useful quantum algorithms;
- polynomial hidden-subgroup query complexity does not imply polynomial total runtime;
- information contained in coset states can be distinct from information efficiently extractable by a bounded measurement class;
- a finite hardware scaling law does not establish an asymptotic complexity lower bound.

The retained research question is narrower:

> For explicitly defined families of structured quantum inference problems, which representation-theoretic quantities predict the coherent measurement resources required to extract a fixed amount of hidden information?

## 2. Conjecture family

### REGB-RIA-1 — restricted-measurement accessibility

For a chosen finite-group HSP family and a specified measurement class `M_k` acting coherently on at most `k` coset-state registers, define an accessibility functional such as

`A_k = I(H ; Y_k)`

or an equivalent hypothesis-identification information measure.

Test whether representation-side quantities predict the growth of `k`, logical depth, or measurement complexity required to reach a fixed accessibility target.

This is a family-specific empirical/mathematical conjecture, not a universal theorem.

### REGB-RIA-2 — information/algorithm separation

Track separately:

1. oracle/query information;
2. state-preparation cost;
3. coherent measurement complexity;
4. classical post-processing complexity;
5. total logical circuit cost.

A lower bound on one layer does not automatically lower-bound the others.

### REGB-RIA-3 — geometry as an explanatory candidate

For finite compiled instances, compare measured/compiled logical cost with a declared Nielsen-style geometric cost.

A correlation may motivate a theorem program. It does not establish:

`representation dimension -> curvature -> complexity`.

### REGB-RIA-4 — locality as an architecture-bound constraint

Lieb-Robinson or related causal bounds apply only after declaring a physical/logical locality model. Any resulting lower bound is scoped to that model unless separately generalized.

## 3. Candidate representation observables

No one observable is privileged a priori. Candidate features include:

- irrep dimension `d_rho`;
- `log d_rho`;
- Plancherel weight;
- multiplicity structure;
- hidden-subgroup projector rank within an irrep;
- row/column-index entropy under an operationally defined partition;
- number of irreps carrying distinguishable subgroup information;
- coherent coset-register count required by the chosen measurement family.

"Intra-irrep entanglement" is not accepted as a scalar invariant until the register factorization and operational task are specified.

## 4. Mandatory counter-controls

Any serious REGB-RIA investigation must include counterexamples to simplistic narratives.

Required control classes should include:

- Abelian HSP positive controls;
- non-Abelian groups with low-dimensional irreps;
- non-Abelian positive controls with known efficient quantum structure;
- symmetric-group stress cases;
- families with efficient QFT but difficult known HSP extraction.

A conjecture that only distinguishes Abelian from non-Abelian structure has failed the control design.

## 5. Theorem-scope firewalls

Maintain these as explicit non-implications:

`LARGE_IRREP != INEFFICIENT_QFT`

`NON_ABELIAN != OUTSIDE_BQP`

`LOW_SINGLE_REGISTER_INFORMATION != LOW_GENERAL_MEASUREMENT_INFORMATION`

`POLYNOMIAL_QUERY_COMPLEXITY != POLYNOMIAL_TIME_COMPLEXITY`

`GEODESIC_COST_CORRELATION != CIRCUIT_LOWER_BOUND_THEOREM`

`LOCALITY_BOUND_ON_ARCHITECTURE_A != UNIVERSAL_BQP_BOUND`

`GRAPH_ISOMORPHISM_HSP_DIFFICULTY != NP_COMPLETE_LOWER_BOUND`

`FINITE_INSTANCE_SCALING != ASYMPTOTIC_SEPARATION`

`REGB_RIA_EVIDENCE != P_VS_NP_RESULT`

## 6. Positive-control source floor

Future theorem work should bind exact source/theorem scope for at least:

1. **Beals (1997)** — efficient quantum Fourier transforms over symmetric groups. This is a direct control against equating large symmetric-group irreps with QFT hardness.
2. **Ettinger–Hoyer–Knill (2004)** — arbitrary finite-group HSP has polynomial quantum query complexity while their construction may require exponential computation. This sharply separates information acquisition from efficient extraction.
3. **Moore–Russell and related symmetric-group HSP work** — lower bounds for restricted Fourier/coset-state measurement strategies, motivating coherent-register measurement complexity as a target quantity.
4. **Nielsen geometric complexity work** — suitable Finsler/geometric distance can lower-bound circuit size under stated assumptions; it does not by itself connect representation dimension to exponential complexity.

Every use must quote the exact theorem hypothesis. Bibliographic existence alone grants no derived conclusion.

## 7. Evidence ladder

Suggested states:

`CONJECTURE_SEED`

`FINITE_INSTANCE_CORRELATION`

`FAMILY_LEVEL_NUMERICAL_SUPPORT`

`RESTRICTED_MEASUREMENT_LOWER_BOUND`

`FAMILY_LEVEL_ASYMPTOTIC_THEOREM`

`ARCHITECTURE_SPECIFIC_PHYSICAL_BOUND`

`GENERAL_COMPLEXITY_CONSEQUENCE`

Transitions are non-automatic. In particular, hardware evidence cannot jump directly to a general complexity consequence.

## 8. Interface to msk-quantum

`msk-formal-discovery` owns conjecture structure, theorem custody, lower-bound assumptions, and non-implications.

`msk-quantum` may execute finite-instance information-accessibility benchmarks and return receipted evidence including:

- group/problem identity;
- representation observables;
- measurement class;
- coherent-register count;
- mutual information / posterior entropy;
- logical resource use;
- hardware topology and QEC context.

The experiment provider does not promote its own finite result into a complexity theorem.

## 9. Long-horizon theorem program

Only after a robust family-level accessibility phenomenon exists should work proceed toward:

1. a mathematically fixed family of problem distributions;
2. a fixed computational/measurement model;
3. an asymptotic lower bound on information extraction or implementation cost;
4. proof that the bound applies to all algorithms in the stated model rather than one Fourier strategy;
5. an explicit reduction from the target computational problem;
6. a barrier analysis against relativization, natural proofs, algebrization, or other applicable proof-complexity limitations.

Until those arrows exist, REGB remains a disciplined conjecture generator rather than a complexity-separation claim.