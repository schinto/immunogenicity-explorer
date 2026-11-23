# Spec 001: Kohorten-Tabelle mit Filtern

| Feld | Wert |
|---|---|
| Status | **Entwurf** (noch nicht eingefroren) |
| Risiko | low |
| Eingefroren am | – |

> Dieses Spec ist der erste Durchlauf der Software Factory. Es wird vor dem Start lokal
> mit dem EGM-Verfahren geprüft (Goldfish-Review) und dann eingefroren.

## Ziel
Ein Nutzer kann alle Kohorten-Datenpunkte des IDC-Datensatzes in einer Tabelle sehen und
nach Wirkstoff, Indikationskategorie und Verabreichungsweg filtern. Damit wird sichtbar,
dass ein Wirkstoff viele verschiedene ADA-Raten hat, je nach klinischem Kontext.

## Nicht-Ziele
- Keine Diagramme und keine Aggregation über Kohorten hinweg (das ist Spec 002 und 003).
- Keine Vorhersage, kein Modell, keine Sequenzanalyse.
- Keine Sortierung über Spaltenköpfe, keine Volltextsuche, kein CSV-Export.
- Kein Nutzerkonto, kein Schreibzugriff.
- Keine Gestaltungsarbeit über eine lesbare, schlichte Tabelle hinaus.

## Kontext

### Daten
Grundlage ist `data/idc/clinical_trials.csv` aus dem gepinnten IDC-Datensatz
(siehe [DATA.md](../../DATA.md)). Das Laden erledigt `scripts/fetch_data.py`.

Verwendete Spalten, exakt so geschrieben wie im Datensatz:

| Spalte | Bedeutung |
|---|---|
| `IDC Row identifier` | eindeutige Zeilen-ID, zum Beispiel `CT0001_A1_002` |
| `Trial ID` | Studien-ID, zum Beispiel `CT0001` |
| `Molecule Assessed for ADA INN Name` | Wirkstoffname (INN) |
| `Disease Indication Category` | Indikationskategorie, 13 feste Werte |
| `Therapeutic Route of Administration` | Verabreichungsweg |
| `Number of Patients analyzed for ADA` | Anzahl auf ADA untersuchter Patienten |
| `Number of ADA+ patients` | Anzahl ADA-positiver Patienten |
| `Frequency of ADA+ patients` | ADA-Rate in **Prozent**, 0 bis 100 |

Eigenschaften der Daten, die beim Umsetzen zählen:
- Der vollständige Datensatz hat **3334 Zeilen**, davon **3281** mit einem Wert in
  `Number of Patients analyzed for ADA`.
- Die CSV-Datei enthält Zeilenumbrüche innerhalb von Feldern. Sie darf nicht zeilenweise
  gelesen werden, sondern nur über einen CSV-Parser.
- Fehlende Werte bleiben fehlend. Sie werden nie als 0 dargestellt.
- `Frequency of ADA+ patients` ist ein Prozentwert. Median 2,36, Mittelwert 11,66, Maximum 100.

### Bestehender Code
- `src/ida/app.py` enthält die FastAPI-Anwendung mit dem Endpunkt `/health`.
- `tests/conftest.py` stellt die Fixtures `cohorts_csv` und `therapeutics_csv` bereit.
- `tests/fixtures/clinical_trials.sample.csv` hat **33 Zeilen**, davon **30** mit einem Wert
  in `Number of Patients analyzed for ADA`, verteilt auf 13 Indikationskategorien und
  16 Wirkstoffe. Alle Tests arbeiten mit dieser Datei, nie mit dem vollen Datensatz.

### Begriffe
Eine **Kohorte mit Messwert** ist eine Zeile mit einem Wert in
`Number of Patients analyzed for ADA`. Nur diese Zeilen erscheinen in der Tabelle.

## Akzeptanzkriterien

**Laden der Daten**

- **AK1** Gegeben die Fixture-CSV. Wenn die Ladefunktion aufgerufen wird. Dann liefert sie
  genau 30 Kohorten, also nur Zeilen mit einem Wert in `Number of Patients analyzed for ADA`.
- **AK2** Gegeben die Fixture-CSV. Wenn eine Kohorte geladen ist. Dann hat sie die Felder
  `row_id`, `trial_id`, `inn_name`, `indication_category`, `route`, `n_analyzed`,
  `n_ada_positive` und `ada_frequency_percent`. `n_analyzed` und `n_ada_positive` sind
  ganze Zahlen oder fehlend, `ada_frequency_percent` ist eine Dezimalzahl oder fehlend.
- **AK3** Gegeben eine Zeile, deren `Number of ADA+ patients` leer ist. Wenn sie geladen
  wird. Dann ist `n_ada_positive` fehlend und **nicht** 0.
- **AK4** Gegeben eine Datei mit fehlender Pflichtspalte. Wenn die Ladefunktion aufgerufen
  wird. Dann wird ein Fehler mit dem Namen der fehlenden Spalte ausgelöst.

**Filter**

- **AK5** Gegeben die 30 Kohorten. Wenn nach dem Wirkstoff `adalimumab` gefiltert wird.
  Dann enthält das Ergebnis nur Kohorten, deren `inn_name` die Zeichenfolge `adalimumab`
  enthält, unabhängig von Groß- und Kleinschreibung.
- **AK6** Gegeben die 30 Kohorten. Wenn nach der Indikationskategorie
  `Cancer and neoplasms` gefiltert wird. Dann stimmt `indication_category` jeder
  Ergebniszeile genau mit diesem Wert überein.
- **AK7** Gegeben die 30 Kohorten. Wenn Wirkstoff und Verabreichungsweg gleichzeitig
  gesetzt sind. Dann erfüllen alle Ergebniszeilen beide Bedingungen (UND-Verknüpfung).
- **AK8** Gegeben die 30 Kohorten. Wenn kein Filter gesetzt ist. Dann werden alle
  30 Kohorten berücksichtigt.

**Weboberfläche**

- **AK9** Gegeben die laufende Anwendung. Wenn `GET /` aufgerufen wird. Dann ist der
  Status 200, der Inhaltstyp HTML, und die Antwort enthält eine Tabelle mit einer Zeile
  je Kohorte sowie die Gesamtzahl der Treffer als Text.
- **AK10** Gegeben mehr Treffer als die Seitengröße von 50. Wenn `GET /` ohne Parameter
  aufgerufen wird. Dann enthält die Seite höchstens 50 Datenzeilen und einen Hinweis auf
  die Gesamtzahl.
- **AK11** Gegeben die laufende Anwendung. Wenn `GET /?inn=adalimumab` aufgerufen wird.
  Dann enthält die Tabelle nur Zeilen dieses Wirkstoffs, und die Filterfelder zeigen den
  gesetzten Wert weiterhin an.
- **AK12** Gegeben die laufende Anwendung. Wenn ein Filterwert ohne Treffer gesetzt wird,
  etwa `GET /?inn=gibtesnicht`. Dann ist der Status 200, die Tabelle ist leer, und es
  erscheint der Hinweis `Keine Treffer`. Es entsteht kein Fehler.
- **AK13** Gegeben die laufende Anwendung. Wenn `GET /?page=0` oder `GET /?page=-1`
  aufgerufen wird. Dann ist der Status 422.
- **AK14** Gegeben die laufende Anwendung. Wenn eine Seite jenseits des letzten Treffers
  angefordert wird. Dann ist der Status 200 mit leerer Tabelle.
- **AK15** Gegeben jede HTML-Seite. Wenn sie gerendert wird. Dann enthält der Seitenfuß
  die Quellenangabe `Immunogenicity Database Collaborative`, den Lizenzhinweis `CC BY 4.0`
  und die DOI `10.3389/fimmu.2026.1816949`.
- **AK15b** Gegeben jede HTML-Seite. Wenn sie gerendert wird. Dann enthält sie einen
  sichtbaren Hinweis, dass ADA-Raten verschiedener Therapeutika ohne klinischen Kontext
  nicht vergleichbar sind und die Darstellung der Forschung dient. Begründung: Die Seite
  wird unter `adam.entreater.com` öffentlich betrieben, siehe `deploy/README.md`.
- **AK16** Gegeben die Tabelle. Wenn eine Kohorte keinen Wert für die ADA-Rate hat. Dann
  zeigt die Zelle einen Strich `–` und nicht `0` oder `nan`.

**JSON-Schnittstelle**

- **AK17** Gegeben die laufende Anwendung. Wenn `GET /api/cohorts` aufgerufen wird. Dann
  ist der Status 200 und die Antwort ein Objekt mit den Schlüsseln `total`, `page`,
  `page_size` und `items`. `items` ist eine Liste mit höchstens 50 Einträgen und den
  Feldnamen aus AK2.
- **AK18** Gegeben die laufende Anwendung. Wenn `GET /api/cohorts?inn=adalimumab`
  aufgerufen wird. Dann gilt dieselbe Filterlogik wie in AK5, und `total` nennt die Anzahl
  aller Treffer, nicht nur die der aktuellen Seite.
- **AK19** Gegeben eine Kohorte ohne ADA-Rate. Wenn sie über die JSON-Schnittstelle
  ausgeliefert wird. Dann ist `ada_frequency_percent` gleich `null`.

**Allgemein**

- **AK20** Gegeben das Projekt. Wenn `./check.sh` ausgeführt wird. Dann endet es mit
  Exitcode 0 und der letzten Zeile `CHECK OK`.
- **AK21** Gegeben die Testsuite. Wenn sie ohne Netzzugriff läuft. Dann ist sie grün. Kein
  Test lädt Daten aus dem Netz und keiner liest `data/idc/`.

## Datei-Plan

| Datei | Zweck |
|---|---|
| `src/ida/models.py` | Datenklasse `Cohort` mit den Feldern aus AK2 |
| `src/ida/data.py` | CSV laden, Spalten prüfen, Kohorten filtern, Seiten bilden |
| `src/ida/app.py` | Endpunkte `/` und `/api/cohorts`, Abhängigkeit zum Datenzugriff |
| `src/ida/templates/base.html` | Grundgerüst der Seite samt Seitenfuß mit Quellenangabe |
| `src/ida/templates/index.html` | Filterformular und Tabelle |
| `tests/test_data.py` | Tests zu AK1 bis AK8 |
| `tests/test_web.py` | Tests zu AK9 bis AK16 |
| `tests/test_api.py` | Tests zu AK17 bis AK19 |

Die Anwendung liest den Pfad zur CSV-Datei aus der Umgebungsvariablen `IDA_DATA_DIR`,
Standard ist `data/idc`. Tests setzen sie auf `tests/fixtures`. Dafür müssen die Fixtures
unter dem im Datensatz üblichen Dateinamen auffindbar sein; falls dazu eine Umbenennung
oder ein zweiter Pfadparameter nötig ist, ist das Teil der Umsetzung und im Datei-Plan
nachzutragen.

## Zerlegung (Vorschlag)
1. `models.py` und `data.py`: Laden und Spaltenprüfung, Tests zu AK1 bis AK4.
2. `data.py`: Filter und Seitenbildung, Tests zu AK5 bis AK8.
3. `app.py` und Templates: Endpunkt `/` mit Tabelle und Seitenfuß, Tests zu AK9, AK10, AK15, AK16.
4. `app.py`: Filter in der Oberfläche samt Fehlerfällen, Tests zu AK11 bis AK14.
5. `app.py`: JSON-Schnittstelle, Tests zu AK17 bis AK19.

## Risiken und offene Punkte
- Die CSV-Datei enthält Zeilenumbrüche in Feldern. Wird sie falsch gelesen, stimmen die
  Zeilenzahlen nicht. AK1 fängt das ab.
- Spaltennamen enthalten Leerzeichen und Sonderzeichen. Sie werden nicht umbenannt,
  sondern genau wie oben verwendet.
- Falls die Zahlen aus AK1 nicht reproduzierbar sind, ist die Datenbasis eine andere.
  Dann die Karte blocken und fragen, nicht die Erwartung anpassen.

## Abnahme
Die Holdout-Szenarien liegen **außerhalb dieses Repos** auf dem Host unter
`/srv/factory/holdout/immunogenicity-explorer/001/`. Sie prüfen über HTTP gegen die
laufende Anwendung mit dem vollen Datensatz, insbesondere die Gesamtzahl von
3281 Kohorten, die 159 Kohorten für Adalimumab, die Verteilung auf die 13
Indikationskategorien und das Verhalten bei leeren Treffern.
