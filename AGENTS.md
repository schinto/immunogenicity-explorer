# AGENTS.md

Table of contents for agents. Keep it short. Details are in the linked files.

## What this project is
A web explorer for clinical immunogenicity data (anti-drug antibody rates) based on the
public IDC dataset. Purpose: make visible that a molecule shows very different ADA rates
depending on the clinical context.

- Data source, license and citation requirement: [DATA.md](DATA.md)
- Domain background and scope: [README.md](README.md)
- Specs (binding, frozen): `specs/<nnn>-<name>/spec.md`

## Stack
- Python >= 3.11, dependencies via `uv`
- FastAPI + Jinja2 (server-side rendered HTML, no frontend framework)
- pandas for loading the CSV files
- pytest for tests, ruff for format and lint

## Commands
```bash
uv sync                  # install dependencies
./check.sh               # the gate: format, lint, tests. Must be green.
uv run python scripts/fetch_data.py   # load the dataset into data/idc/ (network required)
uv run uvicorn ida.app:app --reload   # start locally
```

## Rules for agents
1. **The spec is the contract.** Never change a file under `specs/`. If the spec is
   unclear or contradictory: block the card and ask, do not guess.
2. **`./check.sh` must be green** before you request a review. The last line of the
   output belongs in the handover as evidence.
3. **`git status --porcelain` must be empty** before you request a review. Commit
   everything that belongs to the card.
4. **Never weaken tests.** Do not delete tests, no `skip`, no `xfail`, do not remove an
   assertion to get green. If a test fails for a good reason, the code is wrong, not
   the test.
5. **Test first, then code.** Every acceptance criterion gets at least one test.
6. **No background processes, no `sleep`.** Servers in tests only via the TestClient.
7. **At most 3 attempts** for the same command. Then change approach or block.
8. **No network access in tests.** Tests use the fixtures under `tests/fixtures/`.
9. **No new dependencies** unless named in the spec or after asking.
10. **Only implement what is in the spec.** No extra features, no restructuring
    outside the scope.

## Data rules
- The raw data under `data/idc/` is **not** in the repo and is never committed.
- The ADA frequency is given in the dataset as a **percentage** (0 to 100), not as a fraction.
- Rows without `Number of Patients analyzed for ADA` are not a cohort with a measured value
  and are not counted as such.
- Never set missing values to 0. Missing is missing.
- ADA rates of different therapeutics are not directly comparable. The interface must not
  suggest a ranking that omits the clinical context.

## Public operation
This application will be publicly reachable at `adam.entreater.com`. This implies for
every change:
- No secrets in code, in templates or in log output.
- No writes to the file system at runtime. The container runs with
  `read_only: true`.
- Source attribution, license and context notice remain visible on every page.
- No personal data, not even in log lines.
The full requirements are in [deploy/README.md](deploy/README.md).

## Directories
```
src/ida/        application code (package "ida")
tests/          pytest; tests/fixtures/ contains small CSV excerpts
scripts/        helper scripts (data retrieval)
specs/          specs, frozen. specs/TEMPLATE.md is the template.
data/idc/       raw data, not in the repo
```
