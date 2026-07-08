# Reproduce

**Reviewers start here.** This area lets you re-run, on your own machine, the
six reproduction gates behind the paper's claims and check the result against the
receipts the paper cites.

```bash
pip install -e ".[dev]"   # core + pytest — numpy; see reproduce/ENVIRONMENT.md
bash reproduce/all.sh    # all six lite gates + PASS/FAIL table, < 60s
```

Each gate also runs standalone:

```bash
bash reproduce/01_synthetic_gf2/run.sh
```

A run prints the gate result, writes a receipt to
`<section>/receipts/latest.json`, and compares its **stable digest** against the
committed `canonical.json`. See [`RECEIPT_SCHEMA.md`](RECEIPT_SCHEMA.md) for the
three-tier receipt system and [`ENVIRONMENT.md`](ENVIRONMENT.md) for the pinned
toolchain.

> **Receipts are frozen.** Each `canonical.json` for sections **01–05** is
> committed and paper-cited (`status=FROZEN`); a reviewer run should report
> `DIGEST=MATCH` (`MISMATCH` means the claim surface changed or the checkout
> differs from the frozen source). Section **06** is the newest gate: its
> canonical is **frozen**; its run reports `DIGEST=MATCH` when the
> reviewer's machine reproduces the frozen claim surface.

## Lite by default

The six **lite** gates need **none** of the optional extras and finish in well
under a minute. Optional dependencies (Lean, the expanded quantum data file,
`pyarrow` + the 43MB parquet) cause the relevant tests to **skip cleanly** —
**a skip is not a failure**, so the gates stay green on a bare machine. Only
section 04's **full** path (`RUN_FULL_REPLAY=1`) runs a real Lake build.

## Claim matrix

Six reproduction gates across six sections; section 01 combines two gate test
files (substrate + GF(2) domain). Lite test counts are reproduced exactly here
(observed `148` total: `54 + 23 + 14 + 18 + 8 + 31`).

| # | Section | Claim (one line) | Test file(s) | Lite tests | Receipt | Dep level | Runtime |
|---|---------|------------------|--------------|:----------:|---------|-----------|--------:|
| 01a | `01_synthetic_gf2` | Bounded-generation **substrate**: grammar enumeration is deterministic & depth-bounded, commutative ops canonicalize, missing operators shrink the enumerable set, receipts round-trip & hash stably, the store dedupes by fiber. | `test_iteration9_bounded_generation_phase_a.py` | 36 | `01_synthetic_gf2/receipts/` | core | < 1s |
| 01b | `01_synthetic_gf2` | The bounded grammar constructs **`xor(u,v)`** — absent from the restricted catalog `Q_0` — the verifier **accepts** it, and fiber dedupe collapses algebraic equivalents. | `test_iteration9_bounded_generation_gf2.py` | 18 | `01_synthetic_gf2/receipts/` | core | < 1s |
| 02 | `02_quantum` | The grammar constructs the angle-difference invariant **`alpha − beta`** — absent from `Q_0` — the quantum-oracle verifier accepts a CHSH-violating certificate above the `2.05` margin, and its fiber matches the built-in `R_diff`. | `test_iteration9_bounded_generation_quantum.py` | 23 | `02_quantum/receipts/` | core¹ | < 1s |
| 03 | `03_lean_generation` | The **Lean 4.31.0 kernel** certifies admissibility `Adm(qgen,c)` **and** semantic novelty (`Not FiberEq`) for the generated abstraction; a bad candidate that drops the consumer-preserving component is **rejected** (exit nonzero). | `test_iteration9_bounded_generation_lean.py` | 14 | `03_lean_generation/receipts/` | Lean² | ~4s |
| 04 | `04_real_corpus_replay` | Lite verifies pinned metadata, forbidden-token gating, and receipt determinism. Full mode (`RUN_FULL_REPLAY=1`) replays `Lean4Axiomatic.Integer.one_mul_one_eqv_one` against a real Lake build. | `test_iteration9_lean_github_replay.py` | 18 (+7 slow) | `04_real_corpus_replay/receipts/` | core lite / heavy full³ | < 1s lite |
| 05 | `05_manifold_store` | The three domains (GF(2), quantum, Lean) **stitch into one** verified-information manifold: distinct records retained, same-fiber aliases merge, a cross-domain pattern links all three, and **the store never certifies** — the verifier stays the trust boundary. | `test_iteration9_manifold_store.py` | 8 | `05_manifold_store/receipts/` | core | < 1s |
| 06 | `06_self_extending_grammar` | A retained, V-certified quotient is **promoted to a new typed atom** (`expand_grammar`) and the `enumerate→verify→retain→promote` loop grows the grammar: every promoted atom was verifier-accepted (the **self-extending theorem** soundness), promotion is deterministic / idempotent / monotone to a fixed point, and `G_0 ⊆ G_1` is **strictly more expressive** (`(u⊕v)⊕w` drops from depth 2 to depth 1). Demonstrated in **two domains**: GF(2) (25 tests) and Lean kernel (6 tests). | `test_iteration9_self_extending_grammar.py`, `test_iteration9_lean_self_extending.py` | 31 | `06_self_extending_grammar/receipts/` | core + Lean | < 1s |

¹ **02** needs the expanded quantum data file, bundled in the repo at
`reproduce/02_quantum/quantum-expanded-data.json` (21KB of real CHSH measurement
data). The `run.sh` script points `MANIFOLD_QUANTUM_DATA` at it automatically;
to use a different copy, set `MANIFOLD_QUANTUM_DATA` or `MANIFOLD_DATA_DIR`.
² **03** needs a Lean toolchain on `PATH` (pinned **4.31.0**); if absent the 14
tests **skip**.
³ **04 full** (`RUN_FULL_REPLAY=1`) additionally needs `pyarrow` + the 43MB
parquet (`04_real_corpus_replay/fetch_data.sh`), a source checkout, and
`elan`/`lake` @ `leanprover/lean4:nightly-2024-06-08`.

## What these gates do NOT claim

- **No selection-from-a-rich-catalog.** Novelty is asserted against the
  restricted demonstration catalog `Q_0` only (which deliberately excludes the
  survivors, e.g. `R_diff`/`R_absdiff`). The repo's full catalog may contain an
  equivalent; the point is that the abstraction was **generated**, not selected.
- **No claim that the store certifies.** The manifold store records existence,
  dedupe, provenance, and cross-domain links; the **verifier** is the sole trust
  boundary (gate 05 asserts this directly).
- **No machine-learning / training claim here.** These six gates are about
  bounded generation + verification + receipts, not the learner.
- **Lite mode asserts the always-on surface.** The lite section-04 gate does
  **not** run a Lake build; that is the `RUN_FULL_REPLAY=1` full path.

## Layout

```
reproduce/
├── README.md            # this file — claim matrix + how to run
├── ENVIRONMENT.md       # pinned Python / deps / Lean toolchain (Phase 1a)
├── RECEIPT_SCHEMA.md    # the three-tier receipt system
├── all.sh               # run every lite gate, print PASS/FAIL table
├── _lib/
│   ├── receipt_tools.py # ALL receipt logic (junit → envelope → digest → compare)
│   └── gate_lib.sh      # thin shared run.sh helper
└── NN_<section>/
    ├── README.md        # claim verbatim, command, runtime, what to look at
    ├── run.sh           # thin: pytest (+ marker) → receipt_tools finalize
    └── receipts/
        ├── canonical.json   # committed (paper-cited); frozen at a clean commit
        └── latest.json      # gitignored; your run's output
```
