# 01 — Synthetic GF(2) gluing

Two gates: the bounded-generation **substrate** and the **GF(2) generation**
claim built on top of it.

## Claim

> **Substrate** (`test_iteration9_bounded_generation_phase_a.py`): grammar
> enumeration is deterministic and bounded by depth; commutative operators
> canonicalize (`u xor v == v xor u`); a grammar missing an operator genuinely
> shrinks the enumerable set; receipts round-trip and hash stably (no
> path/time nondeterminism); the manifold store dedupes by fiber, merges
> aliases, and links patterns without collapsing cross-domain records.
>
> **GF(2) generation** (`test_iteration9_bounded_generation_gf2.py`): the
> bounded grammar over atoms `{0,u,v,w}` with op `xor` constructs **`(u xor v)`**,
> which is **absent from the restricted catalog `Q_0`**; the verifier
> **accepts** it for the target orientation and **rejects** a wrong orientation;
> and fiber dedupe collapses algebraic equivalents to a single accepted fiber.

## Run

```bash
bash reproduce/01_synthetic_gf2/run.sh
```

- **Runtime:** < 1s. **Dependencies:** core only (`numpy`). No skips expected.
- **Lite tests:** 54 (36 substrate + 18 GF(2)).

## Receipt

- `receipts/canonical.json` — committed, paper-cited, frozen in Phase 6 (`status=FROZEN`).
- `receipts/latest.json` — written by this run (gitignored).
- Compare any time: `python3 reproduce/_lib/receipt_tools.py compare --section-dir reproduce/01_synthetic_gf2`

## What to look at

- The gate prints `54 passed` and `MANIFEST_SUMMARY ... gate=PASS`.
- `claim_digest` in `latest.json` is the stable identity of the 54-test claim
  surface; it is identical across machines and across re-runs.

## Not claimed

- Novelty is against the **restricted** `Q_0`, not the repo's full catalog.
- This is the synthetic GF(2) world (16 states); it is the controlled
  substrate, not the real-corpus claim (see section 04).
