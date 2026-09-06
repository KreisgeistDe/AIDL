# AIDL

AIDL ist eine LLM-native, deklarative Sprache für Web-, Business-, verteilte,
cloudbetriebene und offlinefähige Anwendungen.

Dieses Repository enthält sowohl die breite AIDL-Spezifikation als auch eine
inkrementell aufgebaute Referenzimplementierung. Der implementierte und in CI
belegte Toolchain-Umfang ist bewusst kleiner als die vollständig spezifizierte
Sprachoberfläche. Maßgeblich für Implementierungsstatus sind aktueller Code,
Tests, maschinenlesbare Verträge und `TODO.md`.

## Implementierter Toolchain-Stand

Die Referenzimplementierung umfasst aktuell unter anderem:

- einen compiler-owned Parser/AST-, Projekt-, Symbol-, Import- und
  Diagnosepfad unter `tools/`, unabhängig von IntelliJ PSI;
- Canonical IR `0.3.0` mit geschlossenem JSON-Schema und deterministischer
  Serialisierung;
- die produktive `aidl`-CLI, installierbar als Wheel und im Checkout weiterhin
  über `./aidl` ausführbar;
- IR-basierte Kompatibilitätsanalyse und Migrationshinweise;
- compiler-owned Resolution, Completion, Dokumentation, Usages und Rename für
  IDE-/Agenten-Nutzung;
- einen begrenzten TypeScript/Fastify/PostgreSQL-M4-Generatorpfad mit
  Ownership-Markern sowie Petstore-Build-, Runtime- und PostgreSQL-E2E-Tests;
- Golden Fixtures, Kompatibilitätsregressionen, IntelliJ-Checks und
  drift-geschützte Python-/Compiler-/CLI-Gates in GitHub Actions;
- einen reproduzierbaren M9-05-Release-Bundle-Dry-Run mit Manifest,
  SHA-256-Prüfsummen und vollständigem `spec/*.json`-Vertragsinventar bei
  weiterhin deaktivierter Veröffentlichung.

Noch **nicht** vorhanden sind insbesondere verpflichtende Branch Protection,
ein öffentlich publiziertes Toolchain-Pre-Release, Signaturen/Attestierungen,
eine vollständige Runtime für alle spezifizierten Profile oder produktionsreife
Adapter für den gesamten Sprachumfang. Diese Arbeiten sind spätere M9+
Roadmap-Punkte.

## Sprach- und Implementierungsumfang

Die Spezifikation beschreibt unter anderem Core-, Web-, Distributed-, Offline-,
Cloud-, Media- und Realtime-Profile. Ein Eintrag in der Spezifikation oder
Profilregistry ist kein Beweis für vollständige Compiler-, IR-, Generator- oder
Runtime-Unterstützung. Der aktuelle belegte Implementierungsumfang ist in
`docs/12-coverage-and-limits.md`, `SUPPORT.md` und `TODO.md` abgegrenzt.

Ein Modul ist nur ein Namespace. Ein Service ist eine explizite Laufzeit- und
Datenbesitzgrenze. Ein Deployment darf mehrere Services für lokale Entwicklung
zusammenlegen, aber niemals deren Ownership-Regeln aufheben.

## Repository-Struktur

```text
docs/        Spezifikation und implementierungsnahe Verträge
spec/        maschinenlesbare IR-, CLI- und Profilverträge
examples/    Petstore, Calendar Offline und VideoHub
fixtures/    versionierte positive/negative Golden Fixtures
tools/       Compiler, CLI, IR-/Kompatibilitätslogik, Generatoren und Tests
plugins/     IDE-Integration
```

## Mitarbeit, Security und Support

- `CONTRIBUTING.md` beschreibt Beitragsregeln, Change-Scope und lokale/CI-
  Validierungsschritte.
- `SECURITY.md` beschreibt den privaten Security-Meldeweg ohne einen nicht
  vorhandenen E-Mail- oder Drittanbieterkanal zu behaupten.
- `SUPPORT.md` trennt den belegten Support-/Stabilitätsstatus von nur
  spezifizierten Profilen und späteren Roadmap-Flächen.
- `docs/artifact-provenance.md` beschreibt exakt die heute überprüfbare
  M9-05-Provenance-/Integritätsevidenz und grenzt Signaturen, SBOM,
  Attestierungen und öffentliche Veröffentlichung ausdrücklich aus.

## Installation aus einem Checkout

Der M9-04-Paketvertrag ist in `pyproject.toml` definiert. Unterstützt wird
bewusst nur Python `>=3.12,<3.13`; Runtime- und Build-Abhängigkeiten sind dort
exakt gepinnt. Ein lokales Wheel kann standardkonform gebaut und anschließend
in eine frische Umgebung installiert werden:

```bash
python3 -m pip wheel --no-deps --wheel-dir dist .
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install dist/aidl_toolchain-0.0.0-py3-none-any.whl
aidl --help
```

Die Distribution heißt derzeit `aidl-toolchain` und trägt die repository-lokale
Packaging-Baseline `0.0.0`; das ist **keine** veröffentlichte Toolchain-
Releaseversion und wird nicht mit IR-, CLI-Schema- oder Profilversionen
gleichgesetzt. M9-05 kann ein reproduzierbares lokales Bundle samt Manifest,
Checksummen und Release Notes erzeugen; `release/release.json` hält die
Veröffentlichung weiterhin explizit auf `disabled`.

Das Wheel enthält den Compiler/CLI-Code unter `tools` sowie die
maschinenlesbaren JSON-Verträge unter `spec`. Dadurch funktioniert insbesondere
`aidl diff` nach Installation ohne einen Repository-relativen Schema-Pfad. Der
CI-Smoke `python3 tools/package_smoke.py` baut das Artefakt, installiert es in
ein neues venv, wechselt aus dem Checkout heraus und prüft reale Console-
Entry-Point- und Importpfade. Details stehen in `docs/m9-cli-packaging.md`.

## Produktive CLI

`aidl --help` ist für eine installierte Distribution die autoritative
Help-Oberfläche; im Repository verweist `./aidl` auf denselben
`tools.aidl_cli:main`-Entry-Point. Aktuell registriert die CLI genau diese
Befehle:

| Befehl | Implementierter Zweck |
|---|---|
| `check` | Projekt kompilieren/validieren und Diagnosen ausgeben |
| `ir` | Canonical IR erzeugen |
| `plan` | deterministischen Deployment-/Runtime-Plan erzeugen |
| `diff` | zwei Projektstände über Canonical IR vergleichen und klassifizieren |
| `inspect` | eine Deklaration per exaktem FQN inspizieren |
| `dependencies` | direkte und in JSON zusätzlich transitive Deklarationsabhängigkeiten ausgeben |
| `explain` | vorhandene Compilerdiagnosen für eine Deklaration erklären |
| `summary` | begrenzte compiler-owned Projektzusammenfassung ausgeben |
| `impact` | compiler-owned Change-Impact-Evidenz für eine Deklaration ausgeben |
| `resolve` | eine Quellreferenz über Compiler-Symbole auflösen |
| `complete` | Completion aus compiler-owned Sichtbarkeit erzeugen |
| `document` | compiler-owned Quick-Documentation/Diagnostikdaten liefern |
| `usages` | semantische Verwendungen über Compiler-Resolution finden |
| `rename` | konservativen compiler-validierten Rename planen oder anwenden |

Beispiele nach Installation:

```bash
aidl check examples/petstore --format json
aidl ir examples/petstore/m4-app --format json
aidl plan examples/petstore/m4-app --format json
aidl inspect petstore.m4.RunnablePet examples/petstore/m4-app --format json
aidl dependencies petstore.m4.RunnablePet examples/petstore/m4-app --format json
aidl summary examples/petstore/m4-app --format json
```

Im Checkout sind dieselben Aufrufe mit `./aidl` möglich.

Es gibt derzeit **keine** produktiven `aidl build`, `aidl test`, `aidl graph`,
`aidl simulate`, `aidl describe`, `aidl edit`, `aidl compatibility`,
`aidl migrate` oder `aidl deploy` Subcommands. Der reproduzierbare M4-Petstore-
Generatorpfad ist aktuell ein repository-interner Treiber, zum Beispiel
`python3 -m tools.m4_petstore generate`, und kein installierter `aidl build`-
Vertrag.

## Maschinenlesbare Versionsverträge

Die Versionen gehören zu getrennten Vertragsdomänen:

- Canonical IR: `irVersion` `0.3.0`, Schema-ID
  `https://aidl.example/spec/0.3/ir.schema.json` in `spec/ir.schema.json`;
- aktuelles CLI-JSON-Schema: Artefaktversion `7.0.0`, Schema-ID
  `https://aidl.example/spec/cli/7/cli-output.schema.json` in
  `spec/cli-output-v7.schema.json`; die v1-v6-Schemas bleiben eingefroren;
- Profilregistry: `registryVersion` `0.3.0` in
  `spec/profile-registry.json`; die einzelnen Profile tragen unabhängig davon
  ihre eigenen Major-Versionen (aktuell `1`).

Die `https://aidl.example/...` Werte sind stabile JSON-Schema-Identifier im
Repositoryvertrag. Sie sind in diesem Pre-Release-Stand keine Zusage, dass dort
bereits veröffentlichte Download-Endpunkte existieren.

## Agenten-Workflow

Für Coding Agents gilt der compiler-first Workflow aus
`docs/m8-coding-agent-workflow.md`: zuerst `check`, dann `plan` und gezielte
`inspect`/`summary`/`dependencies`/`explain`/`impact`-Abfragen; nach Änderungen
erneut validieren und relevante Tests ausführen. Repository-weites heuristisches
Scannen ist kein Ersatz für fehlgeschlagene compiler-owned Resolution.

## Coverage-Regel

Eine Fähigkeit gilt als **implementiert**, wenn der erforderliche Pfad durch
aktuellen Code und ausführbare Tests/CI belegt ist. Eine nur spezifizierte
Fähigkeit bleibt Spezifikationsumfang. Eine IR-Repräsentation ohne passenden
Generator-/Runtime-Beleg wird nicht als vollständige End-to-End-Unterstützung
bezeichnet. Details und bekannte Grenzen stehen in
`docs/12-coverage-and-limits.md`.

## Status

AIDL ist eine Vor-1.0-Referenzimplementierung und -Spezifikation. Syntax,
Profile und Verträge können sich noch ändern. Canonical IR, CLI-JSON-Schemas,
Profilregistry sowie spätere Generator-/Runtime-/Adapter-Artefakte besitzen
getrennte Versionsdomänen; Stabilität wird nur für die jeweils dokumentierten
und getesteten Verträge beansprucht. `main` ist zum Stand dieses Dokuments noch
nicht durch native Branch Protection gegen direkte Änderungen abgesichert.
