# AGENTS.md

Inhaltsverzeichnis für Agenten. Kurz halten. Details stehen in den verlinkten Dateien.

## Was dieses Projekt ist
Ein Web-Explorer für klinische Immunogenitätsdaten (Anti-Drug-Antibody-Raten) auf Basis des
öffentlichen IDC-Datensatzes. Zweck: sichtbar machen, dass ein Molekül je nach klinischem
Kontext sehr unterschiedliche ADA-Raten zeigt.

- Datenquelle, Lizenz und Zitierpflicht: [DATA.md](DATA.md)
- Fachlicher Hintergrund und Scope: [README.md](README.md)
- Specs (verbindlich, eingefroren): `specs/<nnn>-<name>/spec.md`

## Stack
- Python >= 3.11, Abhängigkeiten über `uv`
- FastAPI + Jinja2 (serverseitig gerendertes HTML, kein Frontend-Framework)
- pandas für das Laden der CSV-Dateien
- pytest für Tests, ruff für Format und Lint

## Befehle
```bash
uv sync                  # Abhängigkeiten installieren
./check.sh               # das Gate: Format, Lint, Tests. Muss grün sein.
uv run python scripts/fetch_data.py   # Datensatz nach data/idc/ laden (Netz nötig)
uv run uvicorn ida.app:app --reload   # lokal starten
```

## Regeln für Agenten
1. **Das Spec ist der Vertrag.** Niemals eine Datei unter `specs/` ändern. Wenn das Spec
   unklar oder widersprüchlich ist: Karte blocken und fragen, nicht raten.
2. **`./check.sh` muss grün sein**, bevor du ein Review anforderst. Die letzte Zeile der
   Ausgabe gehört als Beleg in die Übergabe.
3. **`git status --porcelain` muss leer sein**, bevor du ein Review anforderst. Alles
   committen, was zur Karte gehört.
4. **Tests nie abschwächen.** Keine Tests löschen, kein `skip`, kein `xfail`, keine
   Assertion entfernen, um grün zu werden. Wenn ein Test zu Recht fehlschlägt, ist der
   Code falsch, nicht der Test.
5. **Erst der Test, dann der Code.** Jedes Akzeptanzkriterium bekommt mindestens einen Test.
6. **Keine Hintergrundprozesse, kein `sleep`.** Server im Test nur über den TestClient.
7. **Höchstens 3 Versuche** für denselben Befehl. Danach Ansatz wechseln oder blocken.
8. **Keine Netzzugriffe in Tests.** Tests nutzen die Fixtures unter `tests/fixtures/`.
9. **Keine neuen Abhängigkeiten** ohne Nennung im Spec oder Rückfrage.
10. **Nur das umsetzen, was im Spec steht.** Keine Zusatzfeatures, keine Umbauten
    außerhalb des Scopes.

## Datenregeln
- Die Rohdaten unter `data/idc/` sind **nicht** im Repo und werden nie committet.
- Die ADA-Häufigkeit ist im Datensatz in **Prozent** angegeben (0 bis 100), nicht als Anteil.
- Zeilen ohne `Number of Patients analyzed for ADA` sind keine Kohorte mit Messwert und
  werden nicht als solche gezählt.
- Fehlende Werte niemals auf 0 setzen. Fehlend ist fehlend.
- ADA-Raten verschiedener Therapeutika sind nicht direkt vergleichbar. Die Oberfläche darf
  keine Rangliste suggerieren, die den klinischen Kontext weglässt.

## Öffentlicher Betrieb
Diese Anwendung wird unter `adam.entreater.com` öffentlich erreichbar sein. Daraus folgt
für jede Änderung:
- Keine Geheimnisse im Code, in Vorlagen oder in Protokollausgaben.
- Keine Schreibzugriffe aufs Dateisystem zur Laufzeit. Der Container läuft mit
  `read_only: true`.
- Quellenangabe, Lizenz und Kontexthinweis bleiben auf jeder Seite sichtbar.
- Keine personenbezogenen Daten, auch nicht in Logzeilen.
Die vollständigen Auflagen stehen in [deploy/README.md](deploy/README.md).

## Verzeichnisse
```
src/ida/        Anwendungscode (Paket "ida")
tests/          pytest; tests/fixtures/ enthält kleine CSV-Auszüge
scripts/        Hilfsskripte (Datenabruf)
specs/          Specs, eingefroren. specs/TEMPLATE.md ist die Vorlage.
data/idc/       Rohdaten, nicht im Repo
```
