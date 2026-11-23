# Öffentliche Bereitstellung unter adam.entreater.com

## Ausgangslage auf dem VPS (geprüft am 2026-11-23)
- Öffentliche IP des Servers: **187.127.69.57**
- `radar.entreater.com` zeigt auf **genau diese IP** und wird über Traefik ausgeliefert
  (Container `causal-radar-platform-wikijs-1` und `causal-radar-platform-diagrams-1`).
- Traefik läuft als Container `traefik-traefik-1` im Host-Netz, mit Docker-Provider,
  `exposedbydefault=false`, automatischer Weiterleitung von HTTP auf HTTPS und
  Let's Encrypt über die HTTP-Challenge.
- `adam.entreater.com` hat **noch keinen DNS-Eintrag**.

## Schritt 1: DNS-Eintrag anlegen
Die Zone `entreater.com` wird bei Hostinger verwaltet (Nameserver `ns1.dns-parking.com`
und `ns2.dns-parking.com`), zu bearbeiten unter
`hpanel.hostinger.com/domain/entreater.com/dns`.

Vorhandenes Muster in der Zone:

| Typ | Name | Inhalt | TTL |
|---|---|---|---|
| A | `radar` | 187.127.69.57 | 14400 |
| A | `portfolio` | 187.127.69.57 | 300 |
| ALIAS | `@` | entreater.com.cdn.hstgr.net | 300 |

Neu anzulegen, nach dem Muster von `portfolio`:

| Typ | Name | Inhalt | TTL |
|---|---|---|---|
| A | `adam` | 187.127.69.57 | 300 |

Erst danach kann Let's Encrypt ein Zertifikat ausstellen, weil die HTTP-Challenge den
Namen auflösen muss. Prüfen:

```bash
dig +short adam.entreater.com      # erwartet 187.127.69.57
```

## Schritt 2: Abbild bauen und starten
Auf dem VPS, im Verzeichnis dieses Projekts:

```bash
cd deploy
IDA_VERSION=$(git -C .. rev-parse --short HEAD) docker compose build
IDA_VERSION=$(git -C .. rev-parse --short HEAD) docker compose up -d
```

Der Datensatz wird beim Bauen eingebacken und über SHA-256 geprüft. Das Bauen braucht
Netz, der Betrieb nicht.

## Schritt 3: Prüfen
```bash
docker compose ps                                  # Status und Healthcheck
docker compose logs --tail 50 adam
curl -s https://adam.entreater.com/health          # erwartet {"status":"ok",...}
```

Das Zertifikat kann beim ersten Aufruf einige Sekunden brauchen.

## Auflagen für den öffentlichen Betrieb
Diese Punkte gelten als Anforderungen an jedes Spec, das hier veröffentlicht wird:

1. **Nur öffentliche Daten.** Grundlage ist ausschließlich der IDC-Datensatz (CC BY 4.0).
   Keine internen, unveröffentlichten oder vertraulichen Datensammlungen.
2. **Namensnennung sichtbar.** Jede Seite nennt Quelle, Lizenz und DOI im Fuß.
   Das ist eine Lizenzpflicht, kein Schmuck.
3. **Hinweis auf den Kontext.** Die Seite stellt klar, dass ADA-Raten verschiedener
   Therapeutika ohne klinischen Kontext nicht vergleichbar sind, und dass die Darstellung
   der Forschung dient und keine medizinische oder regulatorische Aussage trifft.
4. **Keine Verwechslung mit internen Werkzeugen.** Die Seite erweckt nicht den Eindruck,
   ein firmeninternes Vorhersagemodell oder nicht veröffentlichte Daten zu enthalten.
5. **Nur Lesen.** Keine Anmeldung, keine Formulare mit Speicherung, kein Schreibzugriff.
   Der Container läuft mit `read_only: true` und ohne Rootrechte.
6. **Keine personenbezogenen Daten**, auch nicht in Protokollen. Traefik ist bereits so
   eingestellt, dass Kopfzeilen und Abfrageparameter nicht mitgeschrieben werden.
7. **Ressourcen begrenzt.** 512 MB Arbeitsspeicher und 0,5 CPU, weil der Server knapp
   bei Speicher ist und keinen Swap hat.

## Reihenfolge im Factory-Ablauf
Die Veröffentlichung ist **kein Agentenschritt**. Die Factory baut, prüft und liefert
einen Pull Request. Nach deinem Merge auf `main` erfolgt die Bereitstellung als bewusster
Schritt, zunächst von Hand nach dieser Anleitung. Erst wenn der Ablauf mehrere Wochen
stabil läuft, lohnt sich eine Automatisierung.

Empfohlen: zuerst das Grundgerüst öffentlich stellen, solange es nur `/health` kennt.
Dann ist die Kette aus DNS, Zertifikat, Traefik und Container bewiesen, bevor die erste
Fachfunktion dazukommt.
