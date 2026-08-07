# Plan-D-Pointer — Safe Start for Codex

Stand: 2026-08-07

Die verifizierte Code-Arbeitskopie liegt unter
`C:\_Local_DEV\repos\safe-start-for-codex` auf `main` mit Remote
`https://github.com/dev-bricks/safe-start-for-codex.git` und HEAD
`153b84f` (lokal und `origin/main` gleich).

Dieser OneDrive-Pfad bleibt für Registry, Dokumentation und Artefakte. Er wird
nicht mehr als Arbeitskopie für nachfolgende Codeänderungen verwendet. Es gab
keinen Move- oder Löschlauf.

## Geschützte Asset-Inventur

| Datei | SHA-256 | Abmessungen | Verwendung / Herkunftsbeleg | Entscheidung |
|---|---|---:|---|---|
| `android-icon-background.png` | `079830D65FB6CDA297C7BCC2C983097494623EFDD9B5491E7CC7C43548284243` | 512×512 | keine Referenz, keine Git-Historie | lokal ignoriert, bleibt unverändert in OneDrive |
| `android-icon-foreground.png` | `7B61F37A8D65D016BE7EFCE0B08EE3AE20B17F3510F09758946AB9E20760984E` | 512×512 | keine Referenz, keine Git-Historie | lokal ignoriert, bleibt unverändert in OneDrive |
| `android-icon-monochrome.png` | `03D935E57049673010E949E469F5166E2C530149022582066F10A43F43EF24F1` | 512×512 | keine Referenz, keine Git-Historie; bytegleich mit `icon.png` und `splash-icon.png` | lokal ignoriert, bleibt unverändert in OneDrive |
| `favicon.png` | `F6F8E27B9C53D81C81971599328135A68086B21C24412DE9D4767AA43139D666` | 32×32 | keine Referenz, keine Git-Historie | lokal ignoriert, bleibt unverändert in OneDrive |
| `icon.png` | `03D935E57049673010E949E469F5166E2C530149022582066F10A43F43EF24F1` | 512×512 | keine Referenz, keine Git-Historie; bytegleich mit zwei anderen Dateien | lokal ignoriert, bleibt unverändert in OneDrive |
| `splash-icon.png` | `03D935E57049673010E949E469F5166E2C530149022582066F10A43F43EF24F1` | 512×512 | keine Referenz, keine Git-Historie; bytegleich mit zwei anderen Dateien | lokal ignoriert, bleibt unverändert in OneDrive |

Die Auswertung beruht auf Referenzsuche außerhalb von `assets/`, Git-Historie,
SHA-256 und PNG-Abmessungen, nicht auf Dateinamen. Die Dateien wurden nicht
kopiert, verschoben, gelöscht oder zum lokalen Clone übernommen. Die genaue
fachliche Herkunft bleibt offen; der präzise lokale Ausschluss schützt den
fremden Bestand bis zu einer belegten Zuordnung.
