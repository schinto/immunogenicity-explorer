# Immunogenicity Explorer

Ein kleiner Web-Explorer für klinische Immunogenitätsdaten: Wie häufig bilden Patienten
Antikörper gegen ein Biotherapeutikum (Anti-Drug-Antibodies, ADA), und wie stark hängt das
vom klinischen Kontext ab?

Grundlage ist der öffentliche IDC-Datensatz (CC BY 4.0), siehe [DATA.md](DATA.md).

## Warum
Dieselbe Substanz zeigt je nach Indikation, Dosierung, Begleitmedikation und ADA-Assay
sehr unterschiedliche ADA-Raten. Aggregierte Einzelwerte pro Molekül verdecken das.
Dieser Explorer zeigt die Kohorten einzeln, mit ihrem Kontext.

Adalimumab hat im Datensatz zum Beispiel 159 Kohorten-Datenpunkte, nicht einen Wert.

## Scope
Dieses Projekt dient zugleich als Pilotprojekt für eine Software Factory: Es wird
spec-getrieben von Agenten gebaut. Deshalb ist der Umfang pro Schritt klein und die
Akzeptanzkriterien sind maschinell prüfbar.

Geplante Specs:
1. **Kohorten-Tabelle** mit Filtern (Wirkstoff, Indikation, Verabreichungsweg) – `specs/001-kohorten-tabelle/`
2. **Detailseite pro Therapeutikum**: alle Kohorten mit Streuung der ADA-Rate
3. **Vergleichsdiagramm**: ADA-Rate nach Indikationstyp und Molekülformat

Nicht im Scope: eigene ADA-Vorhersagemodelle, Sequenz- oder Strukturberechnungen,
Nutzerkonten, Schreibzugriff auf die Daten.

## Schnellstart
```bash
uv sync
uv run python scripts/fetch_data.py     # lädt den Datensatz nach data/idc/
./check.sh                              # Format, Lint, Tests
uv run uvicorn ida.app:app --reload     # http://127.0.0.1:8000
```

Tests brauchen kein Netz; sie nutzen die CSV-Auszüge unter `tests/fixtures/`.

## Für Agenten
Verbindliche Arbeitsregeln stehen in [AGENTS.md](AGENTS.md). Kurzfassung: Das Spec ist der
Vertrag, `./check.sh` muss grün sein, Tests werden nie abgeschwächt.
