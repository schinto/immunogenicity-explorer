# Spec <nnn>: <Titel>

| Feld | Wert |
|---|---|
| Status | Entwurf / **eingefroren** / umgesetzt |
| Risiko | low / medium / high |
| Eingefroren am | JJJJ-MM-TT |

## Ziel
Ein bis drei Sätze: Was kann ein Nutzer danach, was vorher nicht ging?

## Nicht-Ziele
Was ausdrücklich **nicht** Teil dieses Specs ist. Verhindert Scope-Ausweitung.

## Kontext
Was der Umsetzende wissen muss: fachliche Hintergründe, relevante Datenfelder mit exakten
Spaltennamen, Besonderheiten der Daten, bestehende Bausteine im Code.

## Akzeptanzkriterien
Jedes Kriterium ist **maschinell prüfbar** und bekommt mindestens einen Test.
Form: Gegeben / Wenn / Dann.

- **AK1** Gegeben … Wenn … Dann …
- **AK2** …

## Datei-Plan
Welche Dateien entstehen oder werden geändert, mit einem Satz Zweck je Datei.

| Datei | Zweck |
|---|---|
| `src/...` | … |
| `tests/...` | … |

## Zerlegung (Vorschlag)
Kleine Inkremente, je höchstens etwa 200 Zeilen Diff, jedes einzeln testbar.

1. …
2. …

## Risiken und offene Punkte
Was schiefgehen kann, und was bei Unklarheit zu tun ist (blocken und fragen).

## Abnahme
Wie wird am Ende geprüft, ob das Spec erfüllt ist? Verweis auf die Holdout-Szenarien,
die außerhalb dieses Repos liegen.
