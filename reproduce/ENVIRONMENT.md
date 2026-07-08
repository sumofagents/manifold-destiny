# Reproduction Environment

This document pins the software environment for reproducing the claims in this
repository. It is the authoritative reference for **what to install** and **how
the dependency lockfile is generated**.

> Package note: the import package is `manifold_destiny` (dist
> `manifold-destiny`). The frozen receipt system lives under `reproduce/`.

## Python

- **Reproduction target: CPython 3.12.** The dependency set is resolved
  against Python 3.12.
- The package metadata declares `requires-python = ">=3.9"`; the lite gates have
  been observed green on 3.9.6 and 3.14.4. 3.12 is the canonical, pinned target.

## Dependencies

All third-party imports across `src/manifold_destiny/` (17 modules) were inventoried.
Only **one** third-party package is imported by the package, and it is optional
and import-guarded:

| Package      | Where used (src/manifold_destiny)             | Guarded? | Bucket               |
|--------------|-----------------------------------------------|----------|----------------------|
| `pyarrow`    | `iteration9_lean_github_replay.py`            | yes (`pyarrow_available()`) | `lean-github` extra |

One more third-party package is used only by an out-of-package script and is
exposed as an extra so that script remains reproducible:

| Package      | Where used                                    | Bucket               |
|--------------|-----------------------------------------------|----------------------|
| `numpy` + `matplotlib` | `scripts/generate_paper_figures.py`  | `figures` extra      |

**Not a dependency:** `pypdf` (and any other PDF library) is **not imported
anywhere** in the repository — verified by grep across `*.py`.

The lite reproduction gates (`-m "not slow"`) require **none** of the extras:
the `pyarrow` import site is guarded and the matching tests skip cleanly when
the dep is absent.

### Install profiles

```bash
# Core only — enough for the six lite reproduction gates:
pip install -e ".[dev]"

# Plus a specific capability:
pip install ".[figures]"        # regenerate paper figures (numpy + matplotlib)
pip install ".[lean-github]"    # real Lean/GitHub corpus replay (pyarrow + 43MB parquet)
```

## Lean / Lake toolchain

Pinned for the frozen reproduction area:

- **Bounded-generation gates:** Lean **4.31.0** (`arm64-apple-darwin24.6.0`
  observed; any 4.31.0 toolchain).
- **Real Lean/GitHub corpus replay** (`-m "not slow"` skips this; full replay
  via `RUN_FULL_REPLAY=1`): Lake toolchain `leanprover/lean4:nightly-2024-06-08`.

Lite gates do not invoke Lake. Lean itself is needed to fully verify section 03
(`03_lean_generation`); without Lean, those tests skip cleanly. Lake + the
pinned nightly toolchain are only required for section 04 full replay.

## Data

The 43MB Lean/GitHub replay parquet is **not** committed (no Git LFS — quota).
It is fetched on demand and SHA256-verified; see
`reproduce/04_real_corpus_replay/fetch_data.sh`. The data
directory is configurable via the `MANIFOLD_DATA_DIR` environment variable.

- Parquet SHA256: `849076288d96d06f68deb5ebcbf65aefba8939fc31b6db897225ea8df26133cb`

## OS notes

- Developed and gated on macOS (arm64, Apple Silicon) and verified on Linux
  (x86_64, Ubuntu). The lite gates use no OS-specific code paths.
- `torch` / `qiskit` (historical extra) pull large, platform-specific wheels;
  install them only when running those experiments.
