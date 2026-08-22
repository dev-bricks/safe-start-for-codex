# Security Policy

## Deutsch

### Sicherheitslücken melden

Bitte eröffnen Sie **keine öffentlichen Issues** für Sicherheitslücken. Verwenden Sie vorrangig das [GitHub Private Vulnerability Reporting](https://github.com/dev-bricks/safe-start-for-codex/security/advisories/new).

Alternativ erreichen Sie das Sicherheitsteam direkt per E-Mail:
- **Primary Security Contact:** `security@ellmos.ai`
- **Secondary Security Contact:** `support@lukasgeiger.com`

Wir bemühen uns um eine Erstprüfung innerhalb von 48 Stunden und koordinieren Patches vor der Veröffentlichung.

### Geltungsbereich & Sicherheitsarchitektur

1. **Local-First & Zero-Egress:** Safe Start for Codex arbeitet zu 100% lokal und offline. Es werden keine Telemetrie- oder Nutzungsdaten übertragen.
2. **Unprivilegierter User-Mode (Non-Elevation):** Das Tool benötigt und verlangt keine Administrator- bzw. UAC-Rechte. Alle Aktionen verbleiben im Kontext des regulären Benutzers.
3. **Nicht-destruktive Dateioperationen:** Alle Schreibzugriffe auf Codex-Konfigurationen (`~/.codex/automations`) erfolgen atomar über temporäre Dateien mit anschließendem Rename und automatischen Backups (`~/.codex/automation-safe-start`), um Dateibeschädigungen bei Systemabstürzen auszuschließen.
4. **Prozessbehandlung:** Das Bereinigen von verwaisten Prozessen beschränkt sich strikt auf die bekannte Codex-Prozessfamilie (`ChatGPT.exe`, `codex.exe`) unter Berücksichtigung definierter Zombie-Schwellenwerte.

---

## English

### Reporting a Vulnerability

Please **do not open public issues** for security vulnerabilities. We encourage using [GitHub Private Vulnerability Reporting](https://github.com/dev-bricks/safe-start-for-codex/security/advisories/new).

Alternatively, you may contact the security team directly via email:
- **Primary Security Contact:** `security@ellmos.ai`
- **Secondary Security Contact:** `support@lukasgeiger.com`

We aim to acknowledge and triage reports within 48 hours and coordinate fixes before public release.

### Scope & Security Guarantees

1. **Local-First & Zero-Egress:** Safe Start for Codex operates 100% locally and offline. No telemetry, crash logs, or user analytics are transmitted over the network.
2. **Unprivileged User-Mode (Non-Elevation):** The tool requires no administrative or elevated UAC privileges and executes entirely within standard unprivileged user space.
3. **Non-Destructive File Safety:** All automation file modifications (`~/.codex/automations`) use atomic writes via temporary files and automatic snapshot backups (`~/.codex/automation-safe-start`) to prevent corruption during unexpected shutdowns.
4. **Targeted Process Supervision:** Process cleanup is strictly constrained to the recognized Codex desktop process family (`ChatGPT.exe`, `codex.exe`) with explicit zombie timeout safeguards.
