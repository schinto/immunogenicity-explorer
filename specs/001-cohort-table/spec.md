# Spec 001: Cohort table with filters

| Field | Value |
|---|---|
| Status | **Frozen** |
| Risk | low |
| Frozen on | 2026-11-26 |

> Revision 2 (2026-11-24) resolved the first Goldfish design review: data access contract, test
> seam, filter rules, malformed data, markup contract, navigation, escaping, slice plan.
> Revision 3 (2026-11-26) resolves the second review round and a finding on the real data:
> 7 measured rows have a non-whole `Number of ADA+ patients` (AC2 amended, AC4b rewritten),
> cache behaviour after a failed load, the 503 page and AGENTS.md, rate formatting, the 422
> mechanism, validation scope and the AC10 split. AC1, AC3 and AC4 are unchanged; numbers keep
> their meaning, new criteria get new numbers.

## Goal
A user can see all cohort data points with a measured ADA value of the IDC dataset in a table, page through them and
filter them by active substance, indication category and route of administration. This makes
visible that one active substance has many different ADA rates, depending on the clinical context.

## Non-goals
- No charts and no aggregation across cohorts (that is spec 002 and 003).
- No prediction, no model, no sequence analysis.
- No sorting via column headers, no full-text search, no CSV export.
- No user account, no write access.
- No design work beyond a readable, plain table. Filter fields are plain text inputs.

## Context

### Abbreviations
- **ADA**: anti-drug antibodies, antibodies a patient forms against a therapeutic.
- **INN**: International Nonproprietary Name of an active substance (for example `Adalimumab`).
- **IDC**: Immunogenicity Database Collaborative, the source of the dataset (see DATA.md).

### Data
The basis is `data/idc/clinical_trials.csv` from the pinned IDC dataset
(see [DATA.md](../../DATA.md)). Loading is done by `scripts/fetch_data.py`.

Columns used, written exactly as in the dataset:

| Column | Meaning |
|---|---|
| `IDC Row identifier` | unique row ID, for example `CT0001_A1_002` |
| `Trial ID` | trial ID, for example `CT0001` |
| `Molecule Assessed for ADA INN Name` | active substance name (INN) |
| `Disease Indication Category` | indication category, 13 fixed values |
| `Therapeutic Route of Administration` | route of administration |
| `Number of Patients analyzed for ADA` | number of patients analyzed for ADA |
| `Number of ADA+ patients` | number of ADA-positive patients |
| `Frequency of ADA+ patients` | ADA rate in **percent**, 0 to 100 |

Properties of the data that matter for the implementation:
- The full dataset has **3334 rows**, of which **3281** have a value in
  `Number of Patients analyzed for ADA`.
- The CSV file contains line breaks inside fields. It must not be read line by line,
  only via a CSV parser.
- Counts are mostly whole numbers, sometimes with a `.0` suffix (`25.0`). In the pinned
  dataset **7 measured rows** have a non-whole `Number of ADA+ patients` (for example `62.7`,
  `41.76`, rows `CT0670_A1_001` to `_003` and `CT0710_A1_002` to `_005`); the source reports
  them this way and they are kept as decimal numbers. `Number of Patients analyzed for ADA` is
  always whole.
- No measured row lacks an ADA rate or an ADA+ count, and every rate lies between 0 and 100
  (checked 2026-11-26). The rules for missing and malformed values still apply.
- Missing values stay missing. They are never shown as 0.
- `Frequency of ADA+ patients` is a percentage. Median 2.36, mean 11.66, maximum 100.
- Routes include `Subcutaneous`, `Intravenous` and also `Subcutaneous or Intravenous`; this
  is why the route filter matches exactly (see "Filter rules").

### Existing code
- `src/ida/models.py`: dataclass `Cohort` with the fields of AC2 (slice 1).
- `src/ida/data.py`: `load_cohorts(path)` and `MissingColumnError` (slice 1).
- `src/ida/app.py`: FastAPI application with the endpoint `/health`.
- `tests/conftest.py` provides the fixtures `cohorts_csv` and `therapeutics_csv`.
- `tests/fixtures/clinical_trials.sample.csv` has **33 rows**, of which **30** have a value
  in `Number of Patients analyzed for ADA`. Facts about these 30 cohorts that tests may rely on:
  - 15 distinct active substances,
  - 4 cohorts of `Adalimumab`, all with route `Subcutaneous`,
  - 2 cohorts with indication category `Cancer and neoplasms`,
  - routes `Subcutaneous` (16), `Intravenous` (12), `Ophthalmic` (2),
  - **no** cohort without an ADA rate and **no** cohort without an ADA+ count.

### Terms
A **cohort with a measured value** is a row with a value in
`Number of Patients analyzed for ADA`. Only these rows appear in the table and the API.

### Data access contract
- `ida.data.filter_cohorts(cohorts, inn=None, indication=None, route=None) -> list[Cohort]`
  applies the filter rules below and keeps the input order.
- `ida.data.paginate(items, page) -> Page` returns a frozen dataclass
  `Page(total, page, page_size, items)` with the constant `PAGE_SIZE = 50` from `ida.data`.
  Pages are 1-based; page `k` holds items `(k-1)*50` to `k*50-1`. A page beyond the last one
  has an empty `items` list and the real `total`. `paginate` raises `ValueError` for `page < 1`.
- `ida.app.get_cohorts() -> list[Cohort]` is a FastAPI dependency. On its first call it reads
  the environment variable `IDA_DATA_DIR` (default `data/idc`), loads
  `<IDA_DATA_DIR>/clinical_trials.csv` with `load_cohorts` and keeps a **successful** result in
  a module-level cache for the lifetime of the process. Nothing is read at import time.
- A failed load is **not** cached: the next request tries again, so providing the file later
  needs no restart. Two concurrent first requests may both load the file; that is accepted.
  `ida.app.reset_cohorts_cache()` empties the cache; tests call it so every test starts fresh.
- **Any** exception while loading (missing file, unreadable file, `MissingColumnError`,
  `DataFormatError`, parser errors) makes `/` and `/api/cohorts` answer status **503**: `/` as
  an HTML page with the text `Data not available` plus footer and context notice,
  `/api/cohorts` as JSON `{"detail": "Data not available"}`. The exception is logged with its
  type; its message is logged only for `MissingColumnError` and `DataFormatError`, whose
  messages contain nothing but a column name and a row identifier. Row data is never logged.
  `/health` never calls `get_cohorts`.
- Page validation: both endpoints declare `page: int = Query(1, ge=1)`, so FastAPI answers 422
  for `page < 1` or a non-integer `page` before any handler code runs. The endpoints never pass
  an invalid page to `paginate`; its `ValueError` is a guard for direct callers only.
  When the page is invalid **and** the data is unavailable, either 422 or 503 is acceptable;
  no test combines the two.
- Tests never load data through `IDA_DATA_DIR`. Web and API tests replace the dependency with
  `app.dependency_overrides[get_cohorts]`, returning either the fixture cohorts
  (`load_cohorts(cohorts_csv)`) or synthetic `Cohort` objects built in the test.
  `tests/conftest.py` sets `IDA_DATA_DIR` to a non-existent directory for every test (autouse),
  so a test that forgets the override fails with 503 instead of silently reading `data/idc/`.

### Filter rules
| Query parameter | Field | Rule |
|---|---|---|
| `inn` | `inn_name` | case-insensitive substring |
| `indication` | `indication_category` | exact, case-sensitive |
| `route` | `route` | exact, case-sensitive |

- Leading and trailing whitespace of a parameter is removed. An empty value (as sent by an
  empty form field, `?inn=`) means "no filter".
- A cohort whose field is missing never matches an active filter on that field.
- All set filters are combined with AND.

### Page and markup contract (`GET /`)
- One HTML page. Jinja2 autoescaping is on, so every value from the data or the URL is escaped.
- Filter form: method GET, text inputs named `inn`, `indication`, `route`, each showing the
  value currently in effect.
- `<p id="total">` contains `{total} results`, where `total` counts all matching cohorts, not
  only the current page.
- `<table id="cohorts">` with the header columns, in this order: `Trial ID`,
  `Active substance`, `Indication category`, `Route`, `Patients analyzed`, `ADA+ patients`,
  `ADA rate (%)`. The `<tbody>` holds exactly one `<tr>` per cohort of the current page, in
  file order.
- Cell values: the text as loaded; whole counts as integers (`25`); a non-whole ADA+ count and
  the rate with one decimal, formatted with Python's `format(value, ".1f")` (`62.7`, `41.76`
  shows as `41.8`, `4.0`);
  every missing value as the dash `–` (U+2013), never `0`, `None` or `nan`. The JSON interface
  returns the numbers as loaded, without rounding, and `null` for every missing value.
- When the current page has no rows, `<p id="empty">` contains `No results`.
- `<nav id="pagination">` contains a link `Previous` when `page > 1` and a link `Next` when
  `page * 50 < total`. Both links keep the current filter parameters and change only `page`.
  The query string is built with `urllib.parse.urlencode` from the non-empty filter values
  (after trimming) plus `page`, so values containing `&`, `#` or spaces stay intact.
- Footer on the page: the source attribution `Immunogenicity Database Collaborative`, the
  license notice `CC BY 4.0` and the DOI `10.3389/fimmu.2026.1816949`.
- Context notice on the page, exactly: `ADA rates of different therapeutics are not comparable
  without their clinical context. This page serves research only and makes no medical or
  regulatory statement.`
- Every HTML page, including the 503 page of `/`, carries footer and context notice
  (AGENTS.md: "on every page"). JSON responses (`/api/cohorts`, `/health`, 422 validation
  errors, the 503 of `/api/cohorts`) are not pages and carry neither.

### Malformed data
Validation applies to **measured rows only**; rows without a value in
`Number of Patients analyzed for ADA` are skipped before any validation.
- `Number of Patients analyzed for ADA`: a whole number >= 0; `25` and `25.0` load as `25`.
- `Number of ADA+ patients`: a number >= 0. A whole value loads as `int` (`25.0` -> `25`), a
  non-whole value as `float` unchanged (`62.7` -> `62.7`).
- `Frequency of ADA+ patients`: a finite number between 0 and 100 inclusive, loaded as `float`.
- Anything else (for example `abc`, `2.5` patients analyzed, `-1`, `nan`, `inf`, `101`) raises
  `DataFormatError` (a `ValueError`) whose message names the row identifier and the column.
  Nothing is truncated, rounded or guessed.

## Acceptance criteria

**Loading the data** (AC1, AC3, AC4 implemented in slice 1; AC2 amended in revision 3)

- **AC1** Given the fixture CSV. When the loading function is called. Then it returns
  exactly 30 cohorts, i.e. only rows with a value in `Number of Patients analyzed for ADA`.
- **AC2** Given the fixture CSV. When a cohort is loaded. Then it has the fields
  `row_id`, `trial_id`, `inn_name`, `indication_category`, `route`, `n_analyzed`,
  `n_ada_positive` and `ada_frequency_percent`. `n_analyzed` is an integer or missing;
  `n_ada_positive` is an integer, a decimal number (only for a non-whole source value, see
  "Malformed data") or missing; `ada_frequency_percent` is a decimal number or missing.
- **AC3** Given a row whose `Number of ADA+ patients` is empty. When it is loaded.
  Then `n_ada_positive` is missing and **not** 0.
- **AC4** Given a file with a missing required column. When the loading function is
  called. Then an error naming the missing column is raised.
- **AC4b** Given a CSV with measured rows whose `Number of ADA+ patients` is `25.0` and `62.7`.
  When it is loaded. Then the values are `25` (an `int`) and `62.7` (a `float`); nothing is
  truncated or rounded.
- **AC4c** Given a CSV with one measured row whose value is malformed, one file per case:
  `2.5` in `Number of Patients analyzed for ADA`; `abc` or `-1` in `Number of ADA+ patients`;
  `nan`, `inf` or `101` in `Frequency of ADA+ patients`. When it is loaded. Then
  `DataFormatError` is raised and its message contains the row identifier and the column name.
- **AC4d** Given a CSV with a row without a value in `Number of Patients analyzed for ADA` and
  `abc` in `Number of ADA+ patients`. When it is loaded. Then no error is raised and the row is
  not part of the result.

**Filters and pages** (data layer)

- **AC5** Given the 30 fixture cohorts. When filtering with `inn="adalimumab"`. Then the result
  has exactly 4 cohorts and every `inn_name` contains `adalimumab` ignoring case.
- **AC6** Given the 30 fixture cohorts. When filtering with
  `indication="Cancer and neoplasms"`. Then the result has exactly 2 cohorts and every
  `indication_category` equals this value.
- **AC7** Given the 30 fixture cohorts. When filtering with `inn="adalimumab"` and
  `route="Subcutaneous"`. Then the result has exactly 4 cohorts, all satisfying both conditions.
  With `route="Intravenous"` instead, the result is empty.
- **AC8** Given the 30 fixture cohorts. When no filter is set, or every filter is an empty or
  whitespace-only string. Then all 30 cohorts are returned in file order.
- **AC8b** Given 120 synthetic cohorts. When `paginate` is called with page 1, 2, 3 and 4.
  Then `total` is 120 every time, `page_size` is 50, the pages hold 50, 50, 20 and 0 items, and
  page 2 starts with the 51st cohort. `paginate(items, 0)` raises `ValueError`.

**Web interface** (`GET /`)

- **AC9** Given the dependency returns the 30 fixture cohorts. When `GET /` is called. Then the
  status is 200, the content type is HTML, `#cohorts` has 30 body rows and `#total` reads
  `30 results`.
- **AC10** Given 120 synthetic cohorts. When `GET /` is called without parameters. Then
  `#cohorts` has exactly 50 body rows and `#total` reads `120 results`.
- **AC10b** Given 120 synthetic cohorts. When `GET /` is called without parameters. Then the
  pagination has a `Next` link to page 2 but no `Previous` link.
- **AC11** Given the 30 fixture cohorts. When `GET /?inn=adalimumab` is called. Then the table
  has the 4 Adalimumab rows, `#total` reads `4 results`, and the `inn` input shows
  `adalimumab`.
- **AC12** Given the 30 fixture cohorts. When `GET /?inn=doesnotexist` is called. Then the status
  is 200, the table body is empty, `#total` reads `0 results` and `#empty` reads `No results`.
- **AC13** Given the running application. When `GET /?page=0`, `GET /?page=-1` or
  `GET /?page=abc` is called. Then the status is 422.
- **AC14** Given the 30 fixture cohorts. When `GET /?page=2` is called. Then the status is 200,
  the table body is empty, `#total` reads `30 results` and `#empty` reads `No results`.
- **AC15** Given `GET /` with any data. When it is rendered. Then the page contains
  `Immunogenicity Database Collaborative`, `CC BY 4.0` and `10.3389/fimmu.2026.1816949`.
- **AC15b** Given `GET /` with any data. When it is rendered. Then the page contains the context
  notice exactly as written in the page contract.
- **AC16** Given a synthetic cohort with missing `n_ada_positive` and missing
  `ada_frequency_percent`. When `GET /` renders it. Then both cells show `–`, and neither cell
  shows `0`, `None` or `nan`.
- **AC16b** Given a synthetic cohort with `n_ada_positive` 62.7 and `ada_frequency_percent`
  4.0, and another with `n_ada_positive` 25. When `GET /` renders them. Then the cells show
  `62.7`, `4.0` and `25`.
- **AC22** Given `IDA_DATA_DIR` points to a directory without `clinical_trials.csv`, no
  dependency override and a fresh cache. When `GET /` is called. Then the status is 503, the
  HTML contains `Data not available`, the footer and the context notice. `GET /api/cohorts`
  answers 503 with JSON `{"detail": "Data not available"}`, and `GET /health` returns 200.
- **AC22b** Given the situation of AC22. When the fixture data is then written to
  `<IDA_DATA_DIR>/clinical_trials.csv` and `GET /` is called again without a restart. Then the
  status is 200 and `#total` reads `30 results` (a failed load is not cached).
- **AC23** Given 120 synthetic cohorts whose `inn_name` contains `adalimumab`. When
  `GET /?inn=adalimumab` and `GET /?inn=adalimumab&page=2` are called. Then the `Next` link of
  page 1 points to page 2 and keeps `inn=adalimumab`, and page 2 has a `Previous` link to
  page 1 that also keeps `inn=adalimumab`.
- **AC24** Given the running application. When `GET /?inn=<script>alert(1)</script>` is
  called. Then the response does not contain `<script>alert(1)</script>` and does contain
  `&lt;script&gt;`.

**JSON interface** (`GET /api/cohorts`)

- **AC17** Given the 30 fixture cohorts. When `GET /api/cohorts` is called. Then the status is
  200 and the response is an object with the keys `total` (30), `page` (1), `page_size` (50)
  and `items`, a list of 30 objects with exactly the field names from AC2.
- **AC18** Given the 30 fixture cohorts. When `GET /api/cohorts?inn=adalimumab` is called. Then
  `total` is 4 and `items` holds the 4 Adalimumab cohorts. With 120 synthetic cohorts and no
  filter, `total` is 120 and `items` holds 50 entries.
- **AC19** Given a synthetic cohort without an ADA rate and without an ADA+ count. When it is
  delivered via the JSON interface. Then its `ada_frequency_percent` and `n_ada_positive` are
  `null`.
- **AC25** Given the running application. When `GET /api/cohorts?page=0` or `?page=abc` is
  called. Then the status is 422. `page_size` is always 50 and cannot be set by the client.

**General** (apply to every slice)

- **AC20** Given the project. When `./check.sh` is run. Then it ends with exit code 0 and the
  last line `CHECK OK`.
- **AC21** Given the test suite. When it runs without network access. Then it is green. No
  test loads data from the network and none reads `data/idc/`; the autouse fixture from the
  data access contract enforces this for the web and API tests.

## File plan

| File | Purpose | Slice |
|---|---|---|
| `src/ida/models.py` | dataclass `Cohort` (exists) | 1 |
| `src/ida/data.py` | `load_cohorts` with strict number parsing and `DataFormatError`, `filter_cohorts`, `Page`, `paginate`, `PAGE_SIZE` | 1, 2 |
| `src/ida/app.py` | dependency `get_cohorts`, endpoints `/` and `/api/cohorts`, 503 handling | 3, 4, 5 |
| `src/ida/templates/base.html` | page skeleton with footer and context notice | 3 |
| `src/ida/templates/index.html` | filter form, total, table, empty notice, pagination | 3, 4 |
| `tests/conftest.py` | autouse fixture setting `IDA_DATA_DIR` to a non-existent directory and calling `reset_cohorts_cache()`; helper to build synthetic cohorts | 3 |
| `tests/test_data.py` | tests for AC1 to AC8b | 1, 2 |
| `tests/test_web.py` | tests for AC9 to AC16b, AC22 to AC24 | 3, 4 |
| `tests/test_api.py` | tests for AC17 to AC19, AC25 | 5 |

Templates are found relative to `src/ida/` (the package directory), not the working
directory. No new dependency is expected: FastAPI, Jinja2, pandas and httpx (TestClient)
must already be in `pyproject.toml`; if one is missing, block the card and ask.

## Breakdown
Slices run one after another; each starts after the previous one is merged.

1. Done: `models.py` and `data.py` loading, AC1 to AC4 (its number handling is replaced in
   slice 2, see "Risks").
2. `models.py`, `data.py`: number rules (AC2 as amended, AC4b to AC4d), filters and pages
   (AC5 to AC8b).
3. `app.py`, templates, conftest: `get_cohorts` with cache and reset, `GET /` (always page 1 in
   this slice) with table, total, empty notice, footer and context notice, 503 handling.
   AC9, AC10, AC15, AC15b, AC16, AC16b, AC22, AC22b.
4. `app.py`, `index.html`: filter form, `page` parameter and links, escaping. AC10b, AC11 to
   AC14, AC23, AC24.
5. `app.py`: JSON interface. AC17 to AC19, AC25.

AC20 and AC21 apply to every slice.

## Risks and open points
- The CSV file contains line breaks in fields. If it is read incorrectly, the row counts
  are wrong. AC1 catches that.
- Column names contain spaces and special characters. They are not renamed,
  but used exactly as above.
- If the numbers from AC1 or the fixture facts above are not reproducible, the data basis is a
  different one. Then block the card and ask, do not adjust the expectation.
- The full dataset is loaded once per process (about 3300 rows); the deployment limit of
  512 MB is sufficient.
- Query strings may appear in the reverse proxy's access log. Accepted: the parameters are
  public search terms, not personal data.
- Risk stays **low**: the site is public but read-only, serves only public CC BY 4.0 data, has
  no accounts and no personal data; untrusted input is limited to three filter strings and the
  page number (escaped, validated). Very long query strings are not limited by the app; the
  reverse proxy's request size limit applies. Accepted residual risk.
- Slice 1 code truncates non-whole counts (`int(float(...))`). Slice 2 replaces this with the
  number rules above; until then the 7 affected rows load with wrong ADA+ counts.

## Acceptance
The holdout scenarios live **outside this repo** on the host under
`/srv/factory/holdout/immunogenicity-explorer/001/`. They check via HTTP against the
running application with the full dataset, in particular the total of
3281 cohorts, the 159 cohorts for `inn=adalimumab` (verified on 2026-11-24 for the substring
rule; the dataset spells it `Adalimumab` only), the distribution across the 13
indication categories and the behavior for empty results.
