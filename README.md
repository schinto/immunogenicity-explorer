# Immunogenicity Explorer

A small web explorer for clinical immunogenicity data: how often do patients develop
antibodies against a biotherapeutic (anti-drug antibodies, ADA), and how strongly does
that depend on the clinical context?

It is based on the public IDC dataset (CC BY 4.0), see [DATA.md](DATA.md).

## Why
The same substance shows very different ADA rates depending on indication, dosing,
concomitant medication and ADA assay. Aggregated single values per molecule hide that.
This explorer shows the cohorts individually, with their context.

Adalimumab, for example, has 159 cohort data points in the dataset, not one value.

## Scope
This project also serves as a pilot project for a Software Factory: it is built
spec-driven by agents. That is why the scope per step is small and the
acceptance criteria are machine-checkable.

Planned specs:
1. **Cohort table** with filters (active substance, indication, route of administration) – `specs/001-cohort-table/`
2. **Detail page per therapeutic**: all cohorts with the spread of the ADA rate
3. **Comparison chart**: ADA rate by indication type and molecule format

Out of scope: own ADA prediction models, sequence or structure calculations,
user accounts, write access to the data.

## Public operation
The application is meant to be publicly reachable at **https://adam.entreater.com**, following
the same pattern as `radar.entreater.com` on the same server: a container behind
Traefik with a Let's Encrypt certificate. Instructions, prerequisites and the requirements for
public operation are in [deploy/README.md](deploy/README.md).

In short: only public data, source attribution and license on every page, a notice about the
limited comparability of ADA rates, read-only access, limited resources.

## Quick start
```bash
uv sync
uv run python scripts/fetch_data.py     # loads the dataset into data/idc/
./check.sh                              # format, lint, tests
uv run uvicorn ida.app:app --reload     # http://127.0.0.1:8000
```

Tests need no network; they use the CSV excerpts under `tests/fixtures/`.

## For agents
Binding working rules are in [AGENTS.md](AGENTS.md). Summary: the spec is the
contract, `./check.sh` must be green, tests are never weakened.
