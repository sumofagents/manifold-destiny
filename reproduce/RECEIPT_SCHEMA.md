# Reproduction Receipt Schema

This document defines the **three-tier receipt system** used by every gate in
`reproduce/`. It specifies the receipt envelope, exactly **what is hashed vs.
what is metadata**, and how a reviewer's run is compared against the
paper-cited canonical receipt.

All receipt logic lives in one place: **`reproduce/_lib/receipt_tools.py`**.
The `run.sh` scripts are thin — they run pytest and hand the JUnit XML to that
tool. Nothing about a receipt is implemented in bash.

## The three tiers

| Tier | File | Tracked? | Produced by | Role |
|------|------|----------|-------------|------|
| **Canonical** | `<section>/receipts/canonical.json` | **committed** | Phase 6 promotion (frozen commit) | the receipt the **paper cites** |
| **Latest** | `<section>/receipts/latest.json` | **gitignored** | the reviewer's `run.sh` | what **this machine** produced |
| **Digest diff** | — (computed) | — | `receipt_tools.py compare` | MATCH / MISMATCH / PENDING/ERROR |

`.gitignore` contains `reproduce/**/receipts/latest.json`, so a reviewer's run
never dirties the tree. `canonical.json` is **not** ignored and is committed.

> **Status:** Phase 6 is complete. Every `canonical.json` is now
> `"status": "FROZEN"` with a non-null `claim_payload`, a stable
> `claim_digest`, and `provenance.source_commit` pointing to the clean commit
> the receipt was generated from. A reviewer run should report **MATCH**; **PENDING**
> only appears if a future section has not yet been frozen.

## Envelope: `manifold-reproduce-receipt-v1`

```jsonc
{
  "schema": "manifold-reproduce-receipt-v1",
  "section": "01_synthetic_gf2",

  // ---- HASHED: the claim. Machine-independent. ----
  "claim_payload": {
    "kind": "gate_manifest_v1",
    "section": "01_synthetic_gf2",
    "domain_receipt_schema": "manifold-destiny-bounded-generation-v1",
    "test_files": ["tests/...py", "..."],          // sorted
    "claim_tests": ["tests.mod.Class::test_x", ...] // sorted; every COLLECTED case
  },
  "claim_digest": "sha256:<hex>",                   // = stable_digest(claim_payload)

  // ---- NOT HASHED: provenance. Run/environment dependent. ----
  "provenance": {
    "mode": "lite",                  // or "full" (RUN_FULL_REPLAY=1, section 04)
    "gate_exit_code": 0,
    "outcomes": {"total": 54, "passed": 54, "skipped": 0, "failed": 0, "errors": 0},
    "skipped_tests": [],             // which claims this run could NOT verify
    "failed_tests": [],
    "dependencies": {                // capability tokens — make a MISMATCH diagnosable
      "lean_available": true, "lake_available": true,
      "quantum_data_present": true, "pyarrow_available": false
    },
    "runtime_seconds": 0.13,         // wall-clock — volatile
    "python_version": "3.12.x",
    "platform": "darwin-arm64",
    "source_commit": "<git HEAD at run time>",  // informational for latest.json
    "working_tree_dirty": false
  }
}
```

## What is hashed (and why that boundary)

The **stable digest** is `sha256` over the canonical JSON of **only
`claim_payload`**:

```
canonical_json(x) = json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n"
stable_digest(x)  = "sha256:" + sha256(canonical_json(x)).hexdigest()
```

This encoding is **byte-for-byte identical** to
`manifold_destiny.iteration9_bounded_generation_receipts.BoundedGenerationReceiptV1.to_json`,
so a domain receipt hashes the same here and in the package.

**Hashed (`claim_payload`)** — the *claim surface*: the sorted set of every
collected test case (`classname::name`) for the gate at its pinned marker, plus
the section id, the domain receipt schema, and the test files. This is
deterministic and **machine-independent**: `skipif` still *collects* a test
(it reports as skipped, not deselected), so a reviewer **without** Lean or the
quantum data collects the *same* claim surface as a fully equipped machine —
and therefore computes the *same digest*. (Verified: an all-passed run and an
all-skipped run of the same gate produce an identical `claim_digest`.)

**NOT hashed (`provenance`)** — everything that legitimately varies between two
honest runs of the same frozen code. Per the design rules, the digest excludes:

- `runtime_seconds`, wall-clock — timing
- local paths, `platform`, `python_version` — machine
- skip **messages** and the pass/skip/fail **outcomes** — environment
- `source_commit`, `working_tree_dirty` — VCS position of the run

> **Claim identity vs. claim verdict.** The digest pins the *identity* of the
> claim set (same code, same tests). The gate's **pytest exit code** pins the
> *verdict* (did the runnable claims pass). They are separate signals: a
> reviewer lacking Lean gets a green gate (Lean tests *skip*, they don't fail)
> **and** a matching digest (same collected surface), with `provenance` noting
> Lean was unavailable so those specific claims were skipped-not-verified.

### Future enrichment (forward-compatible)

Current frozen canonicals use a `gate_manifest_v1` claim payload: section id,
test files, collected test node ids, and the domain receipt schema identifier.
They do **not** yet embed rich per-domain receipts under `domain_receipts`.
That enrichment is intentionally deferred until the paper text needs richer
machine-readable payloads. The digest/compare contract is agnostic to
`claim_payload`'s internal shape — it hashes whatever is there — so future
`domain_receipts` can be added in a new schema/section without changing the
envelope keys, hashed-vs-not boundary, digest algorithm, or file locations.

## `source_commit` semantics

- **`canonical.json`** → the commit the receipt was **generated FROM** (a clean,
  frozen source commit). The receipt file itself is committed in a **follow-up**
  commit, so the canonical receipt never has to hash a tree that contains
  itself (no self-referential hash).
- **`latest.json`** → informational: the commit the **reviewer ran against**
  (their `git HEAD`). Not used in the digest.

## Compare verdicts and exit codes

`receipt_tools.py compare` / the tail of `finalize`:

| Verdict | Meaning | `compare` exit |
|---------|---------|----------------|
| `MATCH` | reviewer's claim digest == canonical's | 0 |
| `MISMATCH` | digests differ (claim surface changed) | 3 |
| `PENDING` | canonical absent or an unfrozen placeholder | 0 (informational) |
| `ERROR` | `latest.json` missing / no `claim_payload` | 4 |

`finalize` (called by `run.sh`) returns the **authoritative gate exit code**:

1. gate failed (`--gate-rc != 0`) → return the gate's code (**failure dominates**)
2. else canonical missing/placeholder → `0` (PENDING is informational for future/unfrozen sections)
3. else digest MATCH → `0`
4. else digest MISMATCH → `3`

So today (canonical = frozen) a gate is green iff its tests pass **and** its
latest claim surface matches the frozen canonical. A digest MISMATCH against a
frozen canonical additionally fails the run even when pytest passes.

## CLI

```bash
# Written by run.sh; rarely called by hand:
python3 reproduce/_lib/receipt_tools.py finalize \
    --section 01_synthetic_gf2 --section-dir reproduce/01_synthetic_gf2 \
    --junit /tmp/j.xml --files "tests/a.py tests/b.py" --gate-rc 0 --mode lite

# Handy directly:
python3 reproduce/_lib/receipt_tools.py compare --section-dir reproduce/01_synthetic_gf2
python3 reproduce/_lib/receipt_tools.py digest  --file reproduce/01_synthetic_gf2/receipts/latest.json
python3 reproduce/_lib/receipt_tools.py show    --file reproduce/01_synthetic_gf2/receipts/latest.json
```
