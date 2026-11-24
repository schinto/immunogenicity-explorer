# Data source and license

## Source
Immunogenicity Database Collaborative (IDC), Dataset V1 (IDC DS V1).

- Website: https://immunogenicitydb.org
- Repository: https://github.com/Immunogenicity-Database-Collaborative/IDC-DB
- Dataset version: **1.0.0**
- Pinned commit: `f5a381206c37585b1fd2f120d9b188c86360534a`

The data is loaded by `scripts/fetch_data.py` from the pinned commit and verified via
SHA-256. The raw data then lives under `data/idc/` and is not part of the repo.

## License
The IDC dataset is licensed under **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
The license requires attribution. Every publication or redistribution of analyses
of this data names the source and cites the accompanying publication:

> Agnihotri S, Gonzalez-Nolasco B, Monian B, Pattijn S, Ackaert C, Wu P, Kettenberger H,
> Tourdot S, Hickling T, Hu Z, Higgs RE, Leventhal DS (2026).
> The immunogenicity database collaborative: a standardized, publicly available database
> for clinical immunogenicity observations and insights.
> *Frontiers in Immunology* 17:1816949. doi:10.3389/fimmu.2026.1816949

The application shows this notice in the footer of every page.

## Scope (as of version 1.0.0, counted ourselves)
| Table | Rows | Content |
|---|---|---|
| `therapeutics.csv` | 218 | therapeutics with format, species, backbone, approval status |
| `clinical_trials.csv` | 3334 | cohort data points from 726 trials, 111 active substances (INN) |
| `aggregated_ada_values.csv` | – | aggregated ADA values per trial arm |
| `sequences.csv` | 222 | amino acid sequences of the chains |
| `variables_explained.csv` | 75 | column descriptions, the data dictionary |
| `controlled_language.csv` | 111 | allowed values of the categorical fields |

In `clinical_trials.csv`, 3281 rows have a value in
`Number of Patients analyzed for ADA` and therefore count as a cohort with a measured value.

## Important domain notes
- `Frequency of ADA+ patients` is a **percentage** from 0 to 100 (median 2.36; mean 11.66).
- Categories in `Disease Indication Category` (13 values, largest first):
  Cancer and neoplasms, Inflammation and autoimmunity, Neurological, Cardiovascular,
  Healthy Volunteer, Musculoskeletal, Unspecified, Metobolic and endocrine disorders,
  Infectious diseases, Renal and urogenital, Non-inflammatory respiratory diseases,
  Non-inflammatory skin diseases, Blood Disorders.
  The spelling comes from the dataset and is not corrected.
- Categories in `Therapeutic Route of Administration`: Intravenous, Subcutaneous,
  Ophthalmic, Intramuscular, Not Applicable, "Subcutaneous or Intravenous".
- The authors explicitly point out that ADA rates are comparable **only in context**,
  i.e. with assay, indication, dose and concomitant medication. A direct comparison
  between therapeutics without this context is not valid from a domain perspective.

## What this project does not use
Internal or unpublished data collections are not used here. The basis is exclusively
the public dataset named above.
