# 03 — Lean generation

## Claim

> The bounded grammar constructs a quotient target (`x, bXor u v`) absent from
> the demonstration catalog `Q_0`, and the **Lean 4.31.0 kernel certifies**
> both **admissibility** (`Adm(qgen,c)`) **and semantic novelty** (`Not
> FiberEq`). A **bad candidate** that drops the consumer-preserving component is
> **rejected** by the kernel (exit nonzero). The Lean version is captured and
> enforced; the emitted source contains no `sorry`.

## Run

```bash
bash reproduce/03_lean_generation/run.sh
```

- **Runtime:** ~4s (invokes the Lean kernel). **Lite tests:** 14.
- **Dependencies:** a **Lean toolchain on `PATH`**, pinned to **4.31.0** (see
  `reproduce/ENVIRONMENT.md`). If Lean is **absent, all 14 tests skip cleanly**
  (`pytest.mark.skipif(not lean_available())`) and the gate stays green.

## Receipt

- `receipts/canonical.json` — committed, paper-cited, frozen in Phase 6 (`status=FROZEN`).
- `receipts/latest.json` — written by this run (gitignored).
- `provenance.dependencies.lean_available` records whether Lean was found.

## What to look at

- With Lean: `14 passed`, and the run takes a few seconds (real kernel calls).
- Without Lean: `14 skipped`, gate still `PASS`.
- The kernel both **accepts** the admissible+novel target and **rejects** the
  bad candidate — certification, not just a syntactic check.

## Not claimed

- The kernel certifies novelty **against `Q_0`**, not against all of Lean's
  mathlib.
- This gate is the *generated*-abstraction certification; the *real-corpus*
  Lean/Lake replay is section 04.
