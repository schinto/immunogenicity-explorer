# Datenquelle und Lizenz

## Quelle
Immunogenicity Database Collaborative (IDC), Dataset V1 (IDC DS V1).

- Website: https://immunogenicitydb.org
- Repository: https://github.com/Immunogenicity-Database-Collaborative/IDC-DB
- Datensatz-Version: **1.0.0**
- Gepinnter Commit: `f5a381206c37585b1fd2f120d9b188c86360534a`

Die Daten werden von `scripts/fetch_data.py` aus dem gepinnten Commit geladen und über
SHA-256 geprüft. Die Rohdaten liegen danach unter `data/idc/` und sind nicht Teil des Repos.

## Lizenz
Der IDC-Datensatz steht unter **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
Die Lizenz verlangt Namensnennung. Jede Veröffentlichung oder Weitergabe von Auswertungen
aus diesen Daten nennt die Quelle und zitiert die Begleitpublikation:

> Agnihotri S, Gonzalez-Nolasco B, Monian B, Pattijn S, Ackaert C, Wu P, Kettenberger H,
> Tourdot S, Hickling T, Hu Z, Higgs RE, Leventhal DS (2026).
> The immunogenicity database collaborative: a standardized, publicly available database
> for clinical immunogenicity observations and insights.
> *Frontiers in Immunology* 17:1816949. doi:10.3389/fimmu.2026.1816949

Die Anwendung zeigt diesen Hinweis im Fuß jeder Seite.

## Umfang (Stand Version 1.0.0, selbst nachgezählt)
| Tabelle | Zeilen | Inhalt |
|---|---|---|
| `therapeutics.csv` | 218 | Therapeutika mit Format, Spezies, Backbone, Zulassungsstatus |
| `clinical_trials.csv` | 3334 | Kohorten-Datenpunkte aus 726 Studien, 111 Wirkstoffe (INN) |
| `aggregated_ada_values.csv` | – | zusammengefasste ADA-Werte je Studienarm |
| `sequences.csv` | 222 | Aminosäuresequenzen der Ketten |
| `variables_explained.csv` | 75 | Spaltenbeschreibungen, das Datenwörterbuch |
| `controlled_language.csv` | 111 | erlaubte Werte der kategorialen Felder |

In `clinical_trials.csv` haben 3281 Zeilen einen Wert in
`Number of Patients analyzed for ADA` und gelten damit als Kohorte mit Messwert.

## Wichtige fachliche Hinweise
- `Frequency of ADA+ patients` ist ein **Prozentwert** von 0 bis 100 (Median 2,36; Mittel 11,66).
- Kategorien in `Disease Indication Category` (13 Werte, größte zuerst):
  Cancer and neoplasms, Inflammation and autoimmunity, Neurological, Cardiovascular,
  Healthy Volunteer, Musculoskeletal, Unspecified, Metobolic and endocrine disorders,
  Infectious diseases, Renal and urogenital, Non-inflammatory respiratory diseases,
  Non-inflammatory skin diseases, Blood Disorders.
  Die Schreibweise stammt aus dem Datensatz und wird nicht korrigiert.
- Kategorien in `Therapeutic Route of Administration`: Intravenous, Subcutaneous,
  Ophthalmic, Intramuscular, Not Applicable, "Subcutaneous or Intravenous".
- Die Autoren weisen ausdrücklich darauf hin, dass ADA-Raten **nur im Kontext**
  vergleichbar sind, also mit Assay, Indikation, Dosis und Begleitmedikation. Ein direkter
  Vergleich zwischen Therapeutika ohne diesen Kontext ist fachlich nicht zulässig.

## Was dieses Projekt nicht nutzt
Interne oder unveröffentlichte Datensammlungen werden hier nicht verwendet. Grundlage ist
ausschließlich der oben genannte öffentliche Datensatz.
