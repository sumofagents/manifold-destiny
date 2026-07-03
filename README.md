# Manifold Destiny

**Continuous Learning by Consumption of Truth-Verified Structure from the Zero-Information Floor**

Jeremiah Thompson · [jeremiah@jeremiahai.com](mailto:jeremiah@jeremiahai.com)
Justin Horowitz · [justin.horowitz@gmail.com](mailto:justin.horowitz@gmail.com)

📄 [Manifold Destiny (PDF)](paper/main.pdf) · [Typst source](paper/main.typ) · [Reproduce](reproduce/)


---

## Reviewers: start here

```bash
bash reproduce/all.sh
```

Runs all six lite reproduction gates (~5 seconds). On this fully provisioned
author machine, the summary body is:

```
SECTION                  GATE   MODE  P/S/F        DIGEST
01_synthetic_gf2         PASS   lite  54p/0s/0f    MATCH
02_quantum               PASS   lite  23p/0s/0f    MATCH
03_lean_generation       PASS   lite  14p/0s/0f    MATCH
04_real_corpus_replay    PASS   lite  18p/0s/0f    MATCH
05_manifold_store        PASS   lite  8p/0s/0f     MATCH
06_self_extending_grammar PASS   lite  31p/0s/0f    MATCH
RESULT: PASS (all gates green)
```

`DIGEST=MATCH` means your machine reproduced the exact claim surface the authors
froze. All six gates have frozen canonical receipts. Heavy dependencies (Lean,
quantum data, pyarrow) skip cleanly if absent; on a bare machine the `P/S/F`
counts may show skips while frozen-gate digests still match. See
[reproduce/ENVIRONMENT.md](reproduce/ENVIRONMENT.md) for full setup.

## What this is

This repository contains the code, formal gates, and reproduction receipts for
the *Manifold Destiny* preprint. The paper presents a learning architecture in
which the intelligence resides in a verifier, not a model. The Consumptor — a
structured store with no weights, no dynamics, no forward pass — acquires
verified abstractions through binary verifier feedback (accept or reject),
without training. A bounded grammar can construct quotients absent from the
fixed catalog; retained verifier-certified quotients can then be promoted to
typed grammar atoms for later rounds. The verifier retains each quotient only
when it satisfies the same contract as catalog candidates, so soundness is
preserved by construction, including the self-extending grammar mechanism
(the self-extending theorem).

## Claims and non-claims

| What the paper claims | What it does NOT claim |
|---|---|
| Bounded generation crosses the fixed-catalog ceiling in three domains (GF(2), quantum CHSH, Lean kernel) | The system is AGI or exhibits open-ended discovery |
| The verifier-mediated retention invariant holds on real mathematics (218K-row Lean-Github corpus, real Lake builds) | The system invented new theorems |
| The architecture unifies three domains under one verified-information quotient store | The store certifies truth on its own — the verifier is always the trust boundary |

| The self-extending grammar promotes retained verifier-certified quotients to typed atoms while preserving soundness across retained generations (the self-extending theorem) | The system invents new operators, verifiers, or an open-ended grammar class |

## The six formal gates

| Gate | What it proves | Command | Runtime |
|---|---|---|---|
| **01. Synthetic GF(2)** | Grammar constructs `xor(u,v)` absent from restricted catalog `Q_0`; verifier accepts; fiber dedupe collapses algebraic equivalents | `bash reproduce/01_synthetic_gf2/run.sh` | < 1s |
| **02. Quantum** | Grammar constructs `alpha - beta`; verifier accepts a CHSH-violating certificate above its classical margin; fiber matches built-in `R_diff` | `bash reproduce/02_quantum/run.sh` | < 1s |
| **03. Lean generation** | Lean 4.31.0 kernel certifies `Adm(qgen, c)` + semantic novelty; bad candidate rejected | `bash reproduce/03_lean_generation/run.sh` | ~3s |
| **04. Real-corpus replay** | Lite: verifies replay metadata, forbidden-token checks, receipt determinism, and pinned case invariants. Full (`RUN_FULL_REPLAY=1`): replays the real theorem against a real Lake build | `bash reproduce/04_real_corpus_replay/run.sh` | < 1s lite |
| **05. Manifold store** | Three domains stitch into one verified-information quotient; same-fiber aliases merge; store never certifies | `bash reproduce/05_manifold_store/run.sh` | < 1s |
| **06. Self-extending grammar** | Verifier-accepted quotients are promoted to new typed atoms; the enumerate → verify → retain → promote loop grows the grammar across rounds while every promoted atom stays V-certified (the self-extending theorem) | `bash reproduce/06_self_extending_grammar/run.sh` | < 1s |

Full claim matrix and heavy-dep instructions: [reproduce/README.md](reproduce/README.md).

## Install

From this repository:

```bash
git clone https://github.com/sumofagents/manifold-destiny.git
cd manifold-destiny
pip install -e ".[dev]"
```

After package publication, the distribution name will be:

```bash
pip install manifold-destiny
```

Import as `manifold_destiny`:

```python
from manifold_destiny.iteration9_bounded_grammar import Grammar, atom, node
from manifold_destiny.iteration9_gluing_bounded_generation import find_accepted_abstractions
```

## Heavy dependencies

Gates that need Lean, quantum hardware data, pyarrow, or checked-out source repos
**skip cleanly** when those dependencies are absent. To enable full replay:

```bash
# Fetch the 43MB Lean-Github parquet (SHA256-verified)
bash reproduce/04_real_corpus_replay/fetch_data.sh

# Set the shared data root
export MANIFOLD_DATA_DIR=~/.manifold-destiny/data

# Run the full real-corpus replay (needs elan/lake + source repos)
RUN_FULL_REPLAY=1 bash reproduce/04_real_corpus_replay/run.sh
```

See [reproduce/ENVIRONMENT.md](reproduce/ENVIRONMENT.md) for Python version,
toolchain pins, and OS notes.

## Repository layout

```
paper/            Typst source (main.typ), bibliography, figures, compiled PDF
reproduce/        Reviewer reproduction gates + canonical receipts
src/manifold_destiny/  Package code (17 modules)
tests/            8 test files (155 tests across the 6 reproduction gates)
examples/         Small usage examples and historical smoke slices
scripts/          Paper figure generation
```

## Building the paper

```bash
cd paper
typst compile main.typ main.pdf
```

Output: `paper/main.pdf` (currently 28 pages).

## Citation

```bibtex
@misc{manifolddestiny2026,
  title={Manifold Destiny: Continuous Learning by Consumption of Truth-Verified Structure from the Zero-Information Floor},
  author={Thompson, Jeremiah and Horowitz, Justin},
  year={2026},
  note={Preprint},
  url={https://github.com/sumofagents/manifold-destiny}
}
```

## License

MIT.

## Contact

Jeremiah Thompson — [jeremiah@jeremiahai.com](mailto:jeremiah@jeremiahai.com)
Justin Horowitz — [justin.horowitz@gmail.com](mailto:justin.horowitz@gmail.com)

