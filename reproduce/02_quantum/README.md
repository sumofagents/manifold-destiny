# 02 — Quantum oracle

## Claim

> The bounded grammar over atoms `{alpha, beta}` with op `sub` constructs the
> angle-difference invariant **`(alpha − beta)`**, which is **absent from the
> restricted demonstration catalog `Q_0`** (`Q_0` deliberately excludes the
> survivors `R_diff`/`R_absdiff`). The existing quantum-oracle verifier
> **accepts** the generated reduction; its **CHSH `S ≈ 2.294`** clears the
> verifier's classical margin (the test asserts `S > 2.05`); and the generated
> reduction shares the **same fiber signature as the built-in `R_diff`**.
> Controls: missing-operator, fixed-catalog-only, classical surrogate, shuffled
> geometry.

## Run

```bash
bash reproduce/02_quantum/run.sh
```

- **Runtime:** < 1s. **Lite tests:** 23.
- **Dependencies:** core, **plus** the expanded quantum data file
  (`quantum-expanded-data.json`, bundled in this directory — 21KB of real CHSH
  measurement data from superconducting-qubit hardware). The `run.sh` script
  sets `MANIFOLD_QUANTUM_DATA` to the repo-bundled copy automatically; to use a
  different copy, set `MANIFOLD_QUANTUM_DATA` or `MANIFOLD_DATA_DIR` before
  running.
- **Full provenance:** `quantum-data-with-metadata.json` (1.3MB, also bundled)
  ships the complete hardware record — transpiled circuit definitions, job
  metrics, backend metadata, raw measurement counts, and CHSH/entanglement-ladder
  S-values — so a reviewer can audit the data collection end to end. IBM Cloud
  credentials used at collection time are NOT included (see its
  `credentials_info` block); regenerate them via your own IBM Quantum account to
  re-run hardware collection.

## Receipt

- `receipts/canonical.json` — committed, paper-cited, frozen (`status=FROZEN`).
- `receipts/latest.json` — written by this run (gitignored).
- `provenance.dependencies.quantum_data_present` tells you whether the data was
  found; with the bundled file present this is `true`.

## What to look at

- `23 passed`, gate `PASS` (all tests run with the bundled data present).
- The `claim_digest` is identical whether the 23 tests passed or skipped — the
  claim *surface* is machine-independent; only the verdict differs.

## Not claimed

- Novelty is against `Q_0` **only**. The repo's full reduction catalog *does*
  contain `R_diff`; the point is the abstraction was **generated**, not selected.
- No claim of a loophole-free physical Bell test — this is the oracle/data
  replay used by the verifier.
