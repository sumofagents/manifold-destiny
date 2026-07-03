# 05 — Manifold store

## Claim

> The three accepted abstractions — GF(2) `(u xor v)`, quantum `(alpha − beta)`,
> and the Lean-certified target — **stitch into one** shared
> `verified_information_quotient_v1` store. The store:
> retains the three domain records as **distinct local abstractions**; **merges**
> a same-fiber alias (the quantum generated `alpha − beta` and the built-in
> `R_diff` share a fiber); **links all three** under one cross-domain pattern
> node; and **never certifies on its own** — the verifier remains the trust
> boundary. The store checks existence, dedupe, provenance, and cross-domain
> links only.

## Run

```bash
bash reproduce/05_manifold_store/run.sh
```

- **Runtime:** < 1s. **Lite tests:** 8. **Dependencies:** core only (pure
  Python; no Lean / quantum data needed — the fibers are reconstructed from
  canonical signatures). No skips expected.

## Receipt

- `receipts/canonical.json` — committed, paper-cited, frozen in Phase 6 (`status=FROZEN`).
- `receipts/latest.json` — written by this run (gitignored).

## What to look at

- `8 passed`, gate `PASS`.
- `test_store_does_not_certify` is the key assertion: the store is a record /
  dedupe / linking layer, **not** a trust boundary.

## Not claimed

- The store does **not** verify or certify anything; it stitches and dedupes
  *already-verified* records. Trust lives in the per-domain verifiers
  (sections 01–04).
