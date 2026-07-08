# 06 — Self-extending grammar

## Claim

> A retained, verifier-certified quotient is **promoted to a new typed atom** in
> the grammar (`expand_grammar`), and the `enumerate → verify → retain → promote`
> loop (`self_extend_loop`) grows the grammar across rounds. The mechanism is:
>
> - **sound** (the self-extending theorem) — every promoted atom originates from a V-accepted
>   expression and carries its defining `Expr` in `grammar.definitions`, so
>   soundness is preserved by induction over retained generations;
> - **deterministic, idempotent & monotone** — promotion derives a stable `s_…`
>   label from the canonical key (so `u xor v` and `v xor u` promote to the *same*
>   atom), re-accepting a fiber adds nothing, atoms only grow, and the loop halts
>   at a fixed point;
> - **strictly more expressive** — `G_0 ⊆ G_1`, and the promoted atom makes
>   `(u⊕v)⊕w` reachable at **depth 1** in `G_1` though it needs **depth 2** in
>   `G_0`. The promoted atom resolves end-to-end back to its accepted expression.

## Run

```bash
bash reproduce/06_self_extending_grammar/run.sh
```

- **Runtime:** < 1s. **Lite tests:** 31 (25 GF(2) + 6 Lean kernel). **Dependencies:** core (GF(2) tests) + Lean 4.31.0 kernel (6 Lean self-extension tests, skip-if-missing).
  Python; no Lean / quantum data needed). No skips expected.

## Receipt

- `receipts/canonical.json` — committed, paper-cited (frozen, MATCH).
- `receipts/latest.json` — written by this run (gitignored).
- Compare any time: `python3 reproduce/_lib/receipt_tools.py compare --section-dir reproduce/06_self_extending_grammar`

## What to look at

- `31 passed` (25 GF(2) + 6 Lean kernel, all via the internal verifier — no external Lean toolchain required), gate `PASS`.
- `TestBootstrappedSoundness::test_promoted_atom_originates_from_accepted_expression`
  is the key soundness assertion: a promoted atom is never *invented* — its label
  is the `sha8` of the canonical key of a V-accepted expression.
- `TestExpressivenessBridge::test_grammar_hierarchy_is_monotonic` is the
  expressiveness bridge: `G_0`'s expressible set is a **subset** of `G_1`'s.
- `TestSemanticPayload::test_promoted_atom_resolves_end_to_end` shows the promoted
  atom carries typed semantics (its originating `Expr`), not just an opaque hash.

## Not claimed

- **No claim that promotion certifies.** `expand_grammar` only promotes an
  expression the **verifier** already accepted; the grammar grows, but the trust
  boundary stays the verifier (as in section 05).
- **No claim of a completed infinite hierarchy.** The loop is depth- and
  round-bounded; it demonstrates the bootstrap mechanism and its fixed point on
  the synthetic GF(2) seed, not an actually-infinite `{G_0, G_1, G_2, …}`.
- Expressiveness novelty is relative to the **seed grammar `G_0`**, mirroring the
  restricted-`Q_0` convention of sections 01–02.
