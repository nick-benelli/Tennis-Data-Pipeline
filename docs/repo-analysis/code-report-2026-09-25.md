# Tennis-Data-Pipeline — Repository Code Review

**Date:** 2026-09-25
**Reviewer:** GitHub Copilot (senior Python engineer review, requested by repo owner)
**Scope:** Whole repository (`src/`, `scripts/`, `tests/`, `docs/`, `notebooks/`, `data/`, packaging/tooling config)

This is a review only — **no changes were made**. Findings are grouped by
area, graded, and then turned into prioritized, actionable recommendations.

File paths are linked so you can jump straight to the evidence.

---

## 1. Repository Structure

**What's good:**

- The `src/` layout is used correctly: [pyproject.toml](../../pyproject.toml) + hatchling will build the wheel from `src/tennis_data_pipeline/`, and there's no top-level package shadowing it.
- Package boundaries are sensible and consistently applied across *five* parallel top-level subpackages that each mirror the same shape for every data source: [datasources/](../../src/tennis_data_pipeline/datasources/) (fetch raw data) → [handler/](../../src/tennis_data_pipeline/handler/) (clean/transform) → [loader/](../../src/tennis_data_pipeline/loader/) (read persisted checkpoints back in) → [workflows/](../../src/tennis_data_pipeline/workflows/) (orchestration/I/O) → [mapper/](../../src/tennis_data_pipeline/mapper/) (cross-source linking). This is a real, deliberate architecture (documented in [docs/architecture/](../architecture/README.md)), not an accident.
- `scripts/` mirrors the source-specific subpackages (`mapper/`, `sackmann/`, `uk/`, `wta_api/`) 1:1, which makes it easy to find "the CLI entry point for X".
- Dependency direction is disciplined: `workflows` → `loader`/`mapper`/`config`, never the reverse (confirmed in repo memory and by inspection) — this is exactly the kind of layering discipline that keeps a growing pipeline maintainable.
- `__init__.py` files are present everywhere they need to be for the installed package; no directory under `src/` is missing one except `__pycache__` (harmless, gitignored).
- Large modules are being proactively split into subpackages as they grow (e.g. `mapper/matches/` → `mapper/matches/uk_sackmann/{schema,names,pass0,pass1,pass2,pipeline,tournament_ids,outputs,checker}.py`), which is exactly the right instinct once a single file starts doing too much.

**Problems found:**

- **Stray empty directory with an invalid package name.** [src/tennis_data_pipeline/repo-analysis/](../../src/tennis_data_pipeline/repo-analysis/) is empty and not tracked by git. A hyphen in a directory name under `src/` can never be a valid importable Python package (`import tennis_data_pipeline.repo-analysis` is a syntax error), so this can only ever be dead clutter. Delete it.
- **An entire datasource is implemented but not wired into the rest of the architecture.** [datasources/tennis_is_my_life/client.py](../../src/tennis_data_pipeline/datasources/tennis_is_my_life/client.py) (`TennisMyLifeClient`) has no corresponding `handler/`, `loader/`, or `workflows/` module, and no tests — every other datasource (`sackmann`, `tennis_data_uk`, `wta`) has all four layers. It's only used by one throwaway script ([scripts/timl/timl_download_all.py](../../scripts/timl/timl_download_all.py)) that hardcodes a relative output path instead of going through [config/paths.py](../../src/tennis_data_pipeline/config/paths.py) like everything else. This reads as an in-progress feature, not a finished one — worth deciding whether to finish it (add handler/workflows/tests, wire it into the config path system) or clearly mark it experimental.
- **A superseded prototype script sits inside the operational `scripts/` tree.** [scripts/timl/archive/timl_download_all.py](../../scripts/timl/archive/timl_download_all.py) is explicitly self-documented as *"Archived, pre-client version"* of the script one directory up. Git history already preserves old versions of files — an `archive/` subfolder inside `scripts/` invites confusion about which script is "live." Same pattern in docs (see below).
- **A dead prototype module lives in `docs/`, not `src/` or an archive, and its own docstring cross-reference is already broken.** [docs/-My-Notes/link_td_sackmann.py](../-My-Notes/link_td_sackmann.py) is a full standalone matching pipeline (predates and was superseded by `mapper/matches/uk_sackmann/`) that references a `data/parquet/` layout that no longer exists in this repo. Worse: the *current, real* module docstring in [mapper/matches/uk_sackmann/\_\_init\_\_.py](../../src/tennis_data_pipeline/mapper/matches/uk_sackmann/__init__.py) still points readers at `docs/My-Notes/link_td_sackmann.py` (no leading hyphen) — that path doesn't exist; the real directory is `docs/-My-Notes/`. A developer following that docstring hits a dead link.
- **Personal/scratch material is mixed into `docs/`, which otherwise reads as reference documentation.** [docs/-My-Notes/](../-My-Notes/) and [docs/-scratch/](../-scratch/) contain a personal markdown notes file, an old prototype script, an `.xlsx` scratchpad, and a raw HTML dump. None of this is documentation in the sense the rest of `docs/` is (architecture/pipelines/data-sources/scripts reference docs) — the leading-hyphen naming already signals "not real docs," but it still lives in the same tree a new contributor would open looking for architecture docs.
- **`docs/architecture/data-sources/` is an empty directory**, not referenced by any doc (confirmed in prior docs review). Dead clutter.
- **`data/` is a large, actively-growing, git-tracked data lake living inside an installable-package repo.** `data/` is 180 MB on disk, 367 tracked files, including one 19 MB zip ([data/raw/timl/tml-data-260913.zip](../../data/raw/timl/tml-data-260913.zip)) and dozens of multi-MB generated CSVs (e.g. every `data/linked/{atp,wta}/{year}/*_enriched_{year}.csv`). This isn't automatically wrong — the README frames this repo as *"Repository of tennis datasets"* first and a pipeline second — but it does mean:
  - Every clone/CI checkout pulls 180 MB of data that has nothing to do with the installable package.
  - `.git` is already 51 MB and will only grow, since none of this is Git LFS-managed and CSVs are binary-diffed forever.
  - It conflates two different things (a *data product* and a *data pipeline tool*) in one repo, which makes "is this repo a library or a dataset?" genuinely ambiguous to a new contributor — worth an explicit decision (see recommendations).

**Suggested structure change:** see [§9](#9-proposed-repository-structure) at the end of this report.

---

## 2. Packaging and `pyproject.toml`

**What's good:**

- `requires-python = ">=3.12"`, `[project.scripts]` entry point, `[build-system]` (hatchling) are all correctly set up for `uv pip install -e .`.
- Dev tooling is correctly split into `[dependency-groups] dev` (mypy, pytest, pytest-cov, pre-commit, pandas-stubs, types-pyyaml, ipykernel, truststore) rather than main dependencies.
- `[tool.ruff]`, `[tool.pytest.ini_options]`, and `[tool.mypy]` are all centralized in `pyproject.toml` rather than scattered across `setup.cfg`/`mypy.ini`/`pytest.ini` — good, modern practice.

**Problems found:**

- **`ruff` is listed as a runtime dependency AND a dev dependency.** [pyproject.toml](../../pyproject.toml) lines 8-18 (`dependencies`) include `"ruff>=0.16.7"`, and it's *also* in `dependency-groups.dev`. Ruff is a linter/formatter — it has no reason to be installed for every consumer of this package at runtime. This bloats the install for anyone doing `uv pip install tennis-data-pipeline` and is almost certainly a copy/paste artifact. Remove it from `dependencies`.
- **`description = "Add your description here"`** — the `uv init --package` placeholder was never filled in. Trivial but visible to anyone who inspects the package metadata (e.g. on PyPI, `pip show`).
- **No optional-dependency groups.** Nothing here strictly needs one yet, but `openpyxl`/`xlrd` (Excel readers, used only by the UK raw-`.xls` ingestion path) are reasonable candidates for an `[project.optional-dependencies] excel = [...]` group if you ever want a lighter default install — low priority, not a real problem today.
- **No upper bound / no `python-requires` ceiling** is fine (apps generally shouldn't over-constrain), but note `pandas>=3.0.5` has no ceiling either — if pandas ships a breaking major release later, `uv sync` will happily pick it up. Not a bug, just something to be aware of for an app (rather than library) dependency policy.

---

## 3 & 4. Code Quality, Imports, and Package Design

**What's good:**

- **No `sys.path` hacks anywhere** — every script and module imports via the installed `tennis_data_pipeline` package name (`from tennis_data_pipeline.datasources... import ...`), confirmed by spot-checking [scripts/timl/timl_download_all.py](../../scripts/timl/timl_download_all.py) and others. This is exactly right for a `src/`-layout, `pip install -e .` project.
- **No circular imports found**; the `workflows → loader/mapper → config` dependency direction is consistently followed (per repo history and spot checks).
- Config access uses a lazy settings proxy (`from tennis_data_pipeline.config import settings`) rather than each module reading environment variables ad hoc — a clean, centralized pattern.
- Type hints are used pervasively and mypy is wired into `pyproject.toml`.
- Docstring conventions (ruff `D100-D103`, module/class/function docstrings on public API) are actually followed, not just configured — spot-checked several modules and all public functions have docstrings.
- No large "God modules" — the biggest file in `src/` is 559 lines ([mapper/tournaments.py](../../src/tennis_data_pipeline/mapper/tournaments.py)), and several other multi-hundred-line modules exist ([handler/uk/cleaner/common.py](../../src/tennis_data_pipeline/handler/uk/cleaner/common.py) at 495, [workflows/mapper/tournaments.py](../../src/tennis_data_pipeline/workflows/mapper/tournaments.py) at 323). None of these are unreasonable yet, but `mapper/tournaments.py` and `common.py` are the two to watch — if either grows another 100-150 lines, they're good candidates for the same package-split treatment already applied to `mapper/matches/`.

**Problems found:**

- **Two real, currently-unresolved `mypy` errors** in [workflows/mapper/tournaments.py](../../src/tennis_data_pipeline/workflows/mapper/tournaments.py) lines 148 and 150 (`_manual_force_keys`):
  ```
  error: Argument 1 to "add" of "set" has incompatible type
  "tuple[str, str | bytes | date | ... ]"; expected "tuple[str, int, str]"
  ```
  This is because `row.year` from `DataFrame.itertuples()` is typed by mypy/pandas-stubs as a broad union (it doesn't know the column is always an `int`), so the constructed tuple doesn't match the declared `set[tuple[str, int, str]]` return type. This isn't necessarily a runtime bug, but it means the declared return type isn't actually verified — and **these errors are invisible in CI** (see §6) so they'll silently accumulate. Fix by narrowing at the call site, e.g. `int(row.year)`, or by using `.itertuples(name=None)` / explicit column access with a cast.
- **Duplicated year-range CLI parsing across 3+ scripts.** `_parse_year_token`/`parse_years` is duplicated near-verbatim in [scripts/uk/build_uk_tournaments.py](../../scripts/uk/build_uk_tournaments.py), [scripts/uk/clean_uk_data.py](../../scripts/uk/clean_uk_data.py), and [scripts/sackmann/build_sackmann_tournaments.py](../../scripts/sackmann/build_sackmann_tournaments.py) (confirmed via repo history — this is a known, deliberate choice per prior notes, not an oversight). Given the stated goal of "free of ... duplicated logic," this is worth reconsidering now that there are 3+ copies: a small `scripts/_cli_common.py` (or similar) with `parse_years`/`parse_year_token` would remove real duplication without adding a heavyweight abstraction. Flagged as medium priority specifically because it's now duplicated in 3 places, not 2.
- **`loader/tournaments.py` is dead code** — it is a one-line docstring stub (`"""Tournament loader."""`) with no implementation, not imported anywhere in `src/`, `scripts/`, or `tests/`. Either implement it or delete it; a stub module with no `TODO` marker and no test is indistinguishable from an accidental leftover.

---

## 5. Testing

**What's good:**

- Tests broadly mirror package structure (`tests/handler/uk/cleaner/`, `tests/mapper/`, `tests/loader/`, `tests/workflows/mapper/`, `tests/sources/{sackmann,tennis_data_uk,wta}/`).
- Pure-logic modules (`mapper/matches/uk_sackmann/names.py`, `pass1.py`, `pass2.py`, `mapper/tournaments.py`) are extensively unit tested with meaningful edge cases (ambiguous candidates, Unicode name normalization, cross-tournament hard-blocks) rather than just happy-path smoke tests — this is genuinely good behavior-focused testing, not implementation-detail testing.
- Test naming is clear and descriptive (`test_manual_matches_backfill_uk_only_when_no_sackmann_counterpart`, etc.) — reads like documentation.

**Problems found:**

- **No tests at all for the `config` subpackage.** [config/loader.py](../../src/tennis_data_pipeline/config/loader.py) (208 lines — env-var substitution regex, `_SettingsProxy`, `get_settings()` caching) and [config/paths.py](../../src/tennis_data_pipeline/config/paths.py) have zero test coverage. This is exactly the kind of module where a subtle regression (e.g. the `${VAR:default}` substitution bug already found and fixed once per repo history) would silently break every workflow at once — it's the highest-value missing test target in the repo.
- **No tests for three of the four `workflows/` source-specific packages.** `tests/workflows/` only has `mapper/`. There are no tests for [workflows/uk/](../../src/tennis_data_pipeline/workflows/uk/) (`fetch.py`, `clean.py`, `tournaments.py`, `update.py` — 223 lines in `update.py` alone), [workflows/sackmann/](../../src/tennis_data_pipeline/workflows/sackmann/), or [workflows/wta_api/](../../src/tennis_data_pipeline/workflows/wta_api/). These are the orchestration layer that ties I/O + config + handler logic together — a natural place for integration-style tests (e.g. using `tmp_path` + a small fixture CSV) even if the underlying pure functions are already unit-tested elsewhere.
- **No tests for `workflows/_csv_upsert.py`** (`upsert_csv`) — this is a shared primitive used by both the UK and Sackmann tournament workflows, and its `keep="first"` vs `keep="last"` dedup semantics have already caused at least one real bug class (stale orphaned rows, per repo history). A focused unit test suite here (append new rows, overwrite existing key, preserve untouched rows) would be cheap and high-value.
- **No tests for `handler/sackmann/tournaments.py` or `handler/wta_api/tournaments.py`** — only `handler/uk/` has test coverage under `tests/handler/`.
- **No `conftest.py` anywhere in the repo.** Given the amount of repeated DataFrame-fixture construction implied by the test files' sizes (e.g. `tests/mapper/test_mapper_matches.py` at 610 lines), it's likely fixture setup is duplicated per test file rather than shared. Worth auditing whether a `tests/conftest.py` (or per-directory `conftest.py`) would remove duplication — not confirmed as a problem, but worth checking given the file sizes.
- **Flat test discovery (no `__init__.py` in `tests/`) already caused one real collision** (`tests/sources/sackmann/test_client.py` vs `tests/sources/tennis_data_uk/test_client.py`, resolved by renaming) — this is a structural trap that will bite again the next time someone adds a test file with a common basename like `test_client.py` or `test_schema.py`. Worth either adding `__init__.py` files throughout `tests/` (switches to fully-qualified module discovery, permanently eliminating the collision class) or documenting the naming convention prominently (e.g. in a `tests/README.md`) so it isn't rediscovered by accident again.

---

## 6. Tooling

**What's good:**

- **uv** is used consistently and correctly (`uv.lock` committed, `dependency-groups` used properly).
- **Ruff** is well-configured: sensible rule selection (`E`, `W`, `F`, `I`, `B`, `UP`, plus targeted docstring rules `D100-D103` rather than the noisy full `D` group), `line-length = 105`, per-file-ignores for tests, and `notebooks`/`docs` correctly excluded from lint/format since they're not held to the same bar. Ruff check and format both currently pass clean across the whole repo — this is a well-maintained baseline, not just a config that exists on paper.
- **Ruff already covers everything a typical Pylint addition would target** here (unused imports/variables via `F`, import sorting via `I`, common bug patterns via `B`, style via `E`/`W`). There is no meaningful gap Pylint would close for this codebase — **do not add Pylint**; it would be redundant tooling for redundancy's sake, which the user explicitly wants to avoid.
- `.pre-commit-config.yaml` runs `ruff-check --fix` + `ruff-format` — correctly pinned to the same ruff version as the dependency group.
- CI ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)) runs `uv sync --all-groups`, ruff check, ruff format check, and pytest on push/PR.

**Problems found:**

- **mypy is configured but never actually run anywhere — not in CI, not in pre-commit.** It's a dev dependency with a `[tool.mypy]` config block, but [.github/workflows/ci.yml](../../.github/workflows/ci.yml) only runs ruff + pytest, and [.pre-commit-config.yaml](../../.pre-commit-config.yaml) only runs ruff hooks. This is exactly how the 2 real type errors in §3/4 above went unnoticed — the tooling exists but has no enforcement point. This is the single highest-value tooling fix available: add a `uv run mypy` step to CI (and optionally a local pre-commit mypy hook, though pre-commit mypy hooks are notoriously finicky with venvs — a CI-only mypy gate is a perfectly reasonable choice too).
- **No coverage reporting/threshold**, despite `pytest-cov` being a listed dev dependency. It's installed but not invoked (no `--cov` flag in CI, no `[tool.coverage.run]` config). Either use it (e.g. `uv run pytest --cov=tennis_data_pipeline --cov-report=term-missing` in CI) or drop the dependency — an installed-but-unused tool is itself a form of the "unnecessary files/clutter" the user asked about.
- **`truststore` dev dependency's purpose isn't obvious from the repo** — it's used for verifying SSL certs against the OS trust store rather than `certifi`, which is a legitimate thing to want for corporate-proxy environments, but nothing in `src/` visibly imports/uses it. Worth a one-line comment in `pyproject.toml` (or removal if it was an experiment that didn't pan out) so a future reader doesn't have to guess why it's there.

---

## 7. Documentation

**What's good:**

- `docs/architecture/` and `docs/pipelines/` are unusually thorough and (per a prior dedicated docs-review pass) code-grounded and accurate for the pipelines they cover.
- Docstrings throughout `src/` are substantive, not filler (e.g. the `mapper/matches/uk_sackmann/__init__.py` docstring quoted above genuinely explains the 3-pass linking algorithm and its rationale — the kind of thing that saves a new contributor real ramp-up time).
- `docs/scripts/README.md` gives a CLI reference for every script.

**Problems found:**

- **Root [README.md](../../README.md) doesn't mention that this is an installable Python package at all.** It frames the repo purely as *"Repository of tennis datasets"* with no "Installation," "Development setup" (`uv sync`, `uv pip install -e .`, running tests/ruff/pre-commit), or "Usage" section describing the `tennis-data-pipeline` console script or how to run the various pipeline scripts. For a repo the user explicitly wants to be "properly packaged" and "easy for another developer to understand," this is the single biggest documentation gap — right now, a new contributor has to read `docs/architecture/` and infer everything about how to actually get the project running locally.
- **A stale/broken cross-reference inside real source code**: `mapper/matches/uk_sackmann/__init__.py`'s docstring points to `docs/My-Notes/link_td_sackmann.py`, but the actual path has a leading hyphen (`docs/-My-Notes/`). Minor, but it's inside package code (not just a doc file), so it's worth fixing alongside any other doc cleanup.
- `docs/TODO.md` is a 3-line, single-dated scratch list — fine as a personal tracker, but if it's meant to be a durable project artifact it currently reads more like a scratch note than documentation (not a real problem, just noting the inconsistency with the otherwise-thorough `docs/` tree).

---

## 8. Repository Hygiene

**What's good:**

- `.gitignore` correctly covers `.venv/`, `.env`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.DS_Store`, `.coverage`, `.idea/`, `.vscode/` — and it's working: none of these are actually tracked in git (verified directly).
- No secrets/credentials found in tracked files; `.env` is git-ignored and `.env.template` (committed, no real values) documents the expected variables correctly.
- No `__pycache__`, `.pyc`, or other build artifacts are tracked.

**Problems found:**

- **`.gitignore` has significant internal duplication** — entries like `.env`, `.DS_Store`, `__pycache__/`, `venv/` each appear **twice** (once from a generic Python-project template block, once from a later hand-added "MacOS"/"System files"/"Environments" block). It works correctly today, but it's a clutter/maintainability smell in a file that's supposed to be a quick reference — worth deduplicating into one clean list.
- **`*.cfg` is globally gitignored** under a "Local configuration files" comment. This is broad enough to accidentally swallow a legitimate future config file (e.g. `setup.cfg`, a linter's `.cfg` file) without anyone noticing it was never tracked. Consider scoping this to the specific local-override filename pattern actually in use, if there is one, rather than the whole extension.
- **`data/` (180 MB, 367 files) is fully git-tracked**, including one 19 MB zip and dozens of multi-MB generated/derived CSVs (see §1). This is the biggest hygiene item in the repo by volume. It may be entirely intentional given the repo's dataset-distribution purpose, but it's worth an explicit decision rather than default accumulation, since it already makes `.git` 51 MB and both numbers only grow over time.
- **Stale/archived prototype files** (`scripts/timl/archive/timl_download_all.py`, `docs/-My-Notes/link_td_sackmann.py`) — both self-identify as superseded. Git history is the right place for "what did this used to look like," not a live `archive/` folder inside an operational directory.
- Empty directories with no purpose: `src/tennis_data_pipeline/repo-analysis/` (untracked), `docs/architecture/data-sources/` (tracked but empty/unreferenced).

---

## Grading

| Category | Grade | Explanation |
|---|---|---|
| Repository Structure | **B** | Genuinely good `src/`-layout discipline and consistent per-source-layering, held back by a few stray/dead directories, an unfinished datasource, and docs/data mixed into the tree without clear boundaries. |
| Packaging | **B-** | Correct mechanics (hatchling, `src/` layout, dependency groups), but a real ruff-in-runtime-deps bug and an unfilled placeholder description are the kind of thing a careful packaging review should have caught. |
| Code Quality | **B+** | Consistently typed, documented, reasonably sized modules; the only real defects are 2 live mypy errors and modest CLI-parsing duplication. |
| Package / Import Design | **A-** | No path hacks, no circular imports, clean layering, console-script entry point works as intended. This is the strongest area of the repo. |
| Testing | **C+** | Existing tests are high quality and behavior-focused, but coverage has real, structurally important gaps (`config/`, most of `workflows/`, the CSV-upsert primitive) — the parts of the codebase most likely to silently break something across the whole pipeline are the least tested. |
| Tooling | **B-** | uv/ruff setup is excellent and actually enforced; mypy and pytest-cov are configured/installed but never actually run, which defeats their purpose. |
| Documentation | **B-** | Architecture/pipeline docs are excellent once you're inside `docs/`, but the front door (root README) doesn't tell a developer this is an installable package or how to set up a dev environment. |
| Repository Hygiene | **C+** | No committed secrets/artifacts (good baseline), but a large and growing git-tracked data directory, a duplicated `.gitignore`, and a few stale/orphaned files/dirs. |

### Overall: **B-**

This is a well-architected, actively-maintained pipeline with real engineering discipline behind its layering, typing, and testing philosophy — well above average for a solo/small-team data project. The grade is pulled down specifically by gaps between *configured* and *enforced* (mypy/coverage not run in CI), a few small but concrete packaging mistakes (ruff in runtime deps), test coverage gaps concentrated in exactly the modules where a silent break would be most damaging (config, workflows, csv upsert), and a documentation/repo-structure story that doesn't yet reflect "this is an installable package" to a first-time visitor.

---

## Recommendations

### High Priority

1. **Remove `ruff` from `[project] dependencies`** in [pyproject.toml](../../pyproject.toml) — it's already correctly present in `dependency-groups.dev`; having it in both means every runtime install of this package pulls in a linter it will never use.
   ```toml
   dependencies = [
       "openpyxl>=3.1.5",
       "pandas>=3.0.5",
       "pyaml>=26.7.0",
       "pydantic>=2.13.5",
       "pydantic-settings>=2.15.0",
       "python-dotenv>=1.0.1",
       "requests>=2.34.2",
       "urllib3>=2.7.0",
       "xlrd>=2.0.2",
   ]
   ```

2. **Wire mypy into CI.** It's configured and passes almost entirely, but 2 real errors are currently invisible because nothing runs it. Add a step to [.github/workflows/ci.yml](../../.github/workflows/ci.yml):
   ```yaml
   - name: mypy
     run: uv run mypy
   ```
   and fix the 2 existing errors in [workflows/mapper/tournaments.py](../../src/tennis_data_pipeline/workflows/mapper/tournaments.py) (`_manual_force_keys`, lines 148/150) — narrow `row.year` to `int` explicitly before adding to the `set[tuple[str, int, str]]`.

3. **Add tests for `config/loader.py` and `config/paths.py`.** This subpackage has zero coverage despite being the single most cross-cutting module in the codebase (every workflow depends on it) and has already had at least one real, silent bug (the `${VAR:default}` substitution issue, fixed previously but never regression-tested). Suggested minimum: round-trip a `configs/config.yaml`-shaped fixture through `get_settings()`, test `${VAR}`/`${VAR:default}` substitution (set/unset/with-default cases), and test that `_SettingsProxy` lazily defers loading until first attribute access.

4. **Add tests for `workflows/_csv_upsert.py` (`upsert_csv`).** It's a shared primitive behind both the UK and Sackmann tournament pipelines, its dedup semantics (`keep="first"` vs `"last"`) have already caused a real stale-row bug in production data, and it currently has no direct unit tests. Minimum cases: new rows appended, existing key overwritten, untouched rows preserved, empty-existing-file case.

5. **Delete the empty `src/tennis_data_pipeline/repo-analysis/` directory.** It's untracked, empty, and structurally invalid as a Python package name (hyphen) — it can only be accidental clutter.

### Medium Priority

6. **Add tests for the untested `workflows/` and `handler/` subpackages** — `workflows/uk/*`, `workflows/sackmann/*`, `workflows/wta_api/*`, `handler/sackmann/tournaments.py`, `handler/wta_api/tournaments.py`. These are the orchestration/handler layers with zero coverage today; even a small number of `tmp_path`-based integration tests per module (write a fixture CSV in, assert the expected output CSV shape/content) would materially reduce the risk of a silent regression in the pipelines that actually produce the shipped data.

7. **Rewrite the root [README.md](../../README.md) to reflect that this is an installable package**, not just a dataset dump. Add: install/dev-setup instructions (`uv sync`, `uv pip install -e .`), how to run tests/lint (`uv run pytest`, `uv run ruff check .`), a pointer to the console script (`tennis-data-pipeline`), and a short "how the pipeline is organized" paragraph linking to [docs/architecture/README.md](../architecture/README.md). Keep the existing dataset-attribution/licensing content — it's good and should stay — but it currently reads like the *only* purpose of the repo.

8. **Decide what to do with `data/` being fully git-tracked (180 MB).** Options, roughly in order of effort: (a) leave as-is if shipping the dataset alongside the code is a deliberate goal — in that case, document that decision in the README so it's clearly intentional; (b) move large/derived/generated artifacts (e.g. `data/linked/**/*_enriched_*.csv`, the 19 MB zip) to Git LFS; (c) stop tracking generated/derived outputs entirely (treat `data/linked/` and similar as pipeline *output*, regeneratable from raw + code, and gitignore it). Whatever you choose, make it an explicit, documented choice rather than default accumulation — right now it silently inflates every clone.

9. **Finish or clearly scope the `tennis_is_my_life` datasource.** Right now it has a working client but no `handler/`, `workflows/`, tests, or config wiring, and the one script that uses it hardcodes a relative path instead of using [config/paths.py](../../src/tennis_data_pipeline/config/paths.py) like every other source. Either bring it up to parity with the other 3 datasources (handler + workflow + config entry + tests) or explicitly mark it experimental/WIP in a comment/docstring so it isn't mistaken for a finished integration.

10. **Extract the duplicated `parse_years`/`_parse_year_token` CLI helper** (currently copy-pasted in [scripts/uk/build_uk_tournaments.py](../../scripts/uk/build_uk_tournaments.py), [scripts/uk/clean_uk_data.py](../../scripts/uk/clean_uk_data.py), and [scripts/sackmann/build_sackmann_tournaments.py](../../scripts/sackmann/build_sackmann_tournaments.py)) into one shared module, e.g. `scripts/_cli_common.py`. Three copies of the same parsing logic is past the point where the duplication cost outweighs the abstraction cost.

11. **Delete or implement [loader/tournaments.py](../../src/tennis_data_pipeline/loader/tournaments.py).** It's a one-line docstring stub, unimported anywhere — indistinguishable from an accidental leftover.

12. **Either use or drop `pytest-cov`.** It's a dev dependency with no `--cov` invocation anywhere and no coverage config — either wire it into CI (`uv run pytest --cov=tennis_data_pipeline`) so coverage gaps like the ones in §5 are visible going forward, or remove the unused dependency.

### Low Priority / Polish

13. **Fix the placeholder package description** in [pyproject.toml](../../pyproject.toml) (`description = "Add your description here"`).

14. **Fix the stale docstring path** in [mapper/matches/uk_sackmann/\_\_init\_\_.py](../../src/tennis_data_pipeline/mapper/matches/uk_sackmann/__init__.py): `docs/My-Notes/link_td_sackmann.py` → `docs/-My-Notes/link_td_sackmann.py`.

15. **Move `scripts/timl/archive/` and `docs/-My-Notes/link_td_sackmann.py` out of live directories.** Both are self-described superseded prototypes; git history already preserves them, so keeping them "live" in `scripts/`/`docs/` only invites "which one do I run?" confusion. If you want to keep them around for reference, a single top-level `archive/` or `docs/history/` (outside both `scripts/` and the package-adjacent `docs/-My-Notes/`) would be clearer than the current split locations.

16. **Deduplicate [.gitignore](../../.gitignore).** `.env`, `.DS_Store`, `__pycache__/`, and `venv/`-family entries are each listed twice (a generic template block plus a later hand-added block). Works fine today, purely a readability/maintenance cleanup.

17. **Remove the empty `docs/architecture/data-sources/` directory** — unreferenced by any doc.

18. **Add a one-line comment explaining why `truststore` is a dev dependency**, or remove it if it's unused — nothing in `src/` currently imports it.

19. **Add `__init__.py` files throughout `tests/`** (or document the constraint prominently in a `tests/README.md`) to permanently eliminate the "duplicate test-file basename across subdirectories" collision class that has already bitten this repo once.

---

## 9. Proposed Repository Structure

This keeps the existing (good) five-layer-per-source architecture unchanged and only addresses the concrete findings above — it is **not** a generic template.

```
Tennis-Data-Pipeline/
├── README.md                      # rewritten: install/dev/usage + dataset info
├── LICENSE
├── pyproject.toml                 # ruff removed from runtime deps
├── uv.lock
├── .env.template
├── .gitignore                     # deduplicated
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml       # + mypy step
│
├── configs/
│   └── config.yaml
│
├── src/
│   └── tennis_data_pipeline/
│       ├── __init__.py
│       ├── config/                # + tests (see below) — unchanged otherwise
│       ├── datasources/
│       │   ├── sackmann/
│       │   ├── tennis_data_uk/
│       │   ├── wta/
│       │   └── tennis_is_my_life/ # finish (handler/workflows/config) or mark WIP
│       ├── handler/
│       │   ├── sackmann/
│       │   ├── uk/
│       │   └── wta_api/
│       ├── loader/                 # tournaments.py removed (dead stub)
│       ├── mapper/
│       │   ├── matches/uk_sackmann/
│       │   └── tournaments.py
│       └── workflows/
│           ├── _csv_upsert.py      # + tests
│           ├── mapper/
│           ├── sackmann/
│           ├── uk/
│           └── wta_api/
│           # (repo-analysis/ removed — was empty/invalid)
│
├── scripts/
│   ├── _cli_common.py             # NEW: shared parse_years/_parse_year_token
│   ├── mapper/
│   ├── sackmann/
│   ├── uk/
│   ├── wta_api/
│   └── timl/                      # archive/ subfolder removed (see docs/history/)
│
├── tests/
│   ├── config/                    # NEW: loader.py / paths.py coverage
│   ├── handler/
│   │   ├── sackmann/              # NEW
│   │   ├── uk/
│   │   └── wta_api/               # NEW
│   ├── loader/
│   ├── mapper/
│   ├── sources/
│   │   ├── sackmann/
│   │   ├── tennis_data_uk/
│   │   └── wta/
│   └── workflows/
│       ├── _csv_upsert/           # NEW
│       ├── mapper/
│       ├── sackmann/              # NEW
│       ├── uk/                    # NEW
│       └── wta_api/               # NEW
│
├── notebooks/                     # unchanged (already ruff-excluded, reasonable)
│
├── docs/
│   ├── README.md
│   ├── TODO.md
│   ├── architecture/               # data-sources/ (empty) removed
│   ├── pipelines/
│   ├── data-sources/
│   ├── scripts/
│   └── history/                    # NEW: renamed from -My-Notes/-scratch,
│                                   # explicitly labeled "superseded/reference only"
│                                   # (link_td_sackmann.py, notes, scratch files)
│
└── data/                           # size/tracking policy decided explicitly
    ├── raw/
    ├── clean/
    ├── linked/
    ├── mapping/
    └── archive/
```

Key differences from today, all traceable to a specific finding above:

- `src/tennis_data_pipeline/repo-analysis/` removed (empty, invalid package name).
- `loader/tournaments.py` removed (dead stub) — or implemented, if it's actually needed.
- New `tests/config/`, `tests/workflows/{uk,sackmann,wta_api}/`, `tests/handler/{sackmann,wta_api}/`, and a `_csv_upsert` test module — closing the coverage gaps in §5.
- New `scripts/_cli_common.py` — removes the 3x-duplicated year-parsing helper.
- `docs/-My-Notes/` and `docs/-scratch/` consolidated into a single, clearly-labeled `docs/history/` (or deleted, if the content isn't worth keeping around — git history still has it either way).
- `data/` left in place structurally (no change to its internal layout, which is already sensible), but flagged for an explicit tracked-vs-generated policy decision rather than a structural move.
