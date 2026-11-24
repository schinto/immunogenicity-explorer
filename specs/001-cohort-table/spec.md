# Spec 001: Cohort table with filters

| Field | Value |
|---|---|
| Status | **Draft** (not yet frozen) |
| Risk | low |
| Frozen on | – |

> This spec is the first run of the Software Factory. Before the start it is reviewed
> locally with the EGM procedure (Goldfish review) and then frozen.

## Goal
A user can see all cohort data points of the IDC dataset in a table and filter them
by active substance, indication category and route of administration. This makes visible
that one active substance has many different ADA rates, depending on the clinical context.

## Non-goals
- No charts and no aggregation across cohorts (that is spec 002 and 003).
- No prediction, no model, no sequence analysis.
- No sorting via column headers, no full-text search, no CSV export.
- No user account, no write access.
- No design work beyond a readable, plain table.

## Context

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
- Missing values stay missing. They are never shown as 0.
- `Frequency of ADA+ patients` is a percentage. Median 2.36, mean 11.66, maximum 100.

### Existing code
- `src/ida/app.py` contains the FastAPI application with the endpoint `/health`.
- `tests/conftest.py` provides the fixtures `cohorts_csv` and `therapeutics_csv`.
- `tests/fixtures/clinical_trials.sample.csv` has **33 rows**, of which **30** have a value
  in `Number of Patients analyzed for ADA`, spread across 13 indication categories and
  16 active substances. All tests work with this file, never with the full dataset.

### Terms
A **cohort with a measured value** is a row with a value in
`Number of Patients analyzed for ADA`. Only these rows appear in the table.

## Acceptance criteria

**Loading the data**

- **AC1** Given the fixture CSV. When the loading function is called. Then it returns
  exactly 30 cohorts, i.e. only rows with a value in `Number of Patients analyzed for ADA`.
- **AC2** Given the fixture CSV. When a cohort is loaded. Then it has the fields
  `row_id`, `trial_id`, `inn_name`, `indication_category`, `route`, `n_analyzed`,
  `n_ada_positive` and `ada_frequency_percent`. `n_analyzed` and `n_ada_positive` are
  integers or missing, `ada_frequency_percent` is a decimal number or missing.
- **AC3** Given a row whose `Number of ADA+ patients` is empty. When it is loaded.
  Then `n_ada_positive` is missing and **not** 0.
- **AC4** Given a file with a missing required column. When the loading function is
  called. Then an error naming the missing column is raised.

**Filters**

- **AC5** Given the 30 cohorts. When filtering by the active substance `adalimumab`.
  Then the result contains only cohorts whose `inn_name` contains the string `adalimumab`,
  regardless of upper and lower case.
- **AC6** Given the 30 cohorts. When filtering by the indication category
  `Cancer and neoplasms`. Then `indication_category` of every result row matches this
  value exactly.
- **AC7** Given the 30 cohorts. When active substance and route of administration are set
  at the same time. Then all result rows satisfy both conditions (AND combination).
- **AC8** Given the 30 cohorts. When no filter is set. Then all
  30 cohorts are included.

**Web interface**

- **AC9** Given the running application. When `GET /` is called. Then the status is 200,
  the content type is HTML, and the response contains a table with one row per cohort
  as well as the total number of results as text.
- **AC10** Given more results than the page size of 50. When `GET /` is called without
  parameters. Then the page contains at most 50 data rows and a notice of the total
  number.
- **AC11** Given the running application. When `GET /?inn=adalimumab` is called.
  Then the table contains only rows of this active substance, and the filter fields still
  show the value that was set.
- **AC12** Given the running application. When a filter value without results is set,
  for example `GET /?inn=doesnotexist`. Then the status is 200, the table is empty, and
  the notice `No results` appears. No error occurs.
- **AC13** Given the running application. When `GET /?page=0` or `GET /?page=-1`
  is called. Then the status is 422.
- **AC14** Given the running application. When a page beyond the last result is
  requested. Then the status is 200 with an empty table.
- **AC15** Given any HTML page. When it is rendered. Then the footer contains
  the source attribution `Immunogenicity Database Collaborative`, the license notice `CC BY 4.0`
  and the DOI `10.3389/fimmu.2026.1816949`.
- **AC15b** Given any HTML page. When it is rendered. Then it contains a
  visible notice that ADA rates of different therapeutics are not comparable without
  clinical context and that the presentation serves research. Rationale: the page
  is operated publicly at `adam.entreater.com`, see `deploy/README.md`.
- **AC16** Given the table. When a cohort has no value for the ADA rate. Then
  the cell shows a dash `–` and not `0` or `nan`.

**JSON interface**

- **AC17** Given the running application. When `GET /api/cohorts` is called. Then
  the status is 200 and the response is an object with the keys `total`, `page`,
  `page_size` and `items`. `items` is a list with at most 50 entries and the
  field names from AC2.
- **AC18** Given the running application. When `GET /api/cohorts?inn=adalimumab`
  is called. Then the same filter logic as in AC5 applies, and `total` gives the number
  of all results, not only those of the current page.
- **AC19** Given a cohort without an ADA rate. When it is delivered via the JSON
  interface. Then `ada_frequency_percent` is `null`.

**General**

- **AC20** Given the project. When `./check.sh` is run. Then it ends with
  exit code 0 and the last line `CHECK OK`.
- **AC21** Given the test suite. When it runs without network access. Then it is green. No
  test loads data from the network and none reads `data/idc/`.

## File plan

| File | Purpose |
|---|---|
| `src/ida/models.py` | data class `Cohort` with the fields from AC2 |
| `src/ida/data.py` | load CSV, check columns, filter cohorts, build pages |
| `src/ida/app.py` | endpoints `/` and `/api/cohorts`, dependency on data access |
| `src/ida/templates/base.html` | page skeleton including footer with source attribution |
| `src/ida/templates/index.html` | filter form and table |
| `tests/test_data.py` | tests for AC1 to AC8 |
| `tests/test_web.py` | tests for AC9 to AC16 |
| `tests/test_api.py` | tests for AC17 to AC19 |

The application reads the path to the CSV file from the environment variable `IDA_DATA_DIR`,
default `data/idc`. Tests set it to `tests/fixtures`. For this, the fixtures must be
findable under the file name customary in the dataset; if a rename or a second path
parameter is needed for that, it is part of the implementation and must be added to the
file plan.

## Breakdown (proposal)
1. `models.py` and `data.py`: loading and column check, tests for AC1 to AC4.
2. `data.py`: filters and pagination, tests for AC5 to AC8.
3. `app.py` and templates: endpoint `/` with table and footer, tests for AC9, AC10, AC15, AC16.
4. `app.py`: filters in the interface including error cases, tests for AC11 to AC14.
5. `app.py`: JSON interface, tests for AC17 to AC19.

## Risks and open points
- The CSV file contains line breaks in fields. If it is read incorrectly, the row counts
  are wrong. AC1 catches that.
- Column names contain spaces and special characters. They are not renamed,
  but used exactly as above.
- If the numbers from AC1 are not reproducible, the data basis is a different one.
  Then block the card and ask, do not adjust the expectation.

## Acceptance
The holdout scenarios live **outside this repo** on the host under
`/srv/factory/holdout/immunogenicity-explorer/001/`. They check via HTTP against the
running application with the full dataset, in particular the total of
3281 cohorts, the 159 cohorts for adalimumab, the distribution across the 13
indication categories and the behavior for empty results.
