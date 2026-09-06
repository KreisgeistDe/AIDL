# 4. Agenten-Tooling

## Autoritative Oberfläche

Für Agenten ist die aktuelle Referenzimplementierung maßgeblich. Die
registrierten Subcommands kommen aus `tools/aidl_cli.py`; nach Installation ist
`aidl --help` die autoritative Help-Oberfläche. Im Repository verweist `./aidl`
auf denselben `tools.aidl_cli:main`-Entry-Point. Historisch spezifizierte
Befehlsnamen sind kein implementierter Vertrag, solange sie dort nicht
registriert sind.

Die installierbare M9-04-Paketgrenze, Python- und Abhängigkeitspins sowie der
Clean-Machine-Smoke sind in `docs/m9-cli-packaging.md` dokumentiert. Der
ausführbare Repository-Workflow ist in `docs/m8-coding-agent-workflow.md`
beschrieben und durch `tools/test_m8_agent_workflow.py` geschützt.

## Verbindlicher Arbeitszyklus

Die folgenden Befehle verwenden den installierten Console-Entry-Point `aidl`.
In einem Checkout kann jeweils äquivalent `./aidl` verwendet werden.

1. `aidl check ... --format json` auf dem Zielprojekt ausführen.
2. Mit `aidl plan ... --format json` den aktuellen compiler-owned Plan lesen.
3. Zielkontext gezielt mit `inspect`, `summary`, `dependencies`, `explain` oder
   `impact` ermitteln; fehlgeschlagene Compilerauflösung nicht durch
   Repository-Heuristiken ersetzen.
4. Die kleinste fachlich vollständige Quelländerung vornehmen. Die CLI besitzt
   keinen generischen AST-Edit-Subcommand.
5. `check` erneut ausführen und alle Fehler beheben.
6. `plan` und die gezielten Abfragen erneut ausführen.
7. Bei zwei Projektständen `aidl diff` für semantische Fakten,
   Kompatibilitätsklassifikation und vorhandene Migrationshinweise verwenden.
8. Relevante Regressionen und anschließend die normalen Repository-CI-Gates
   ausführen.

Der Prozessvertrag bleibt: Exit `0` für Erfolg, `1` für erwartete
Validierungs-/Auswahl-/Buildfehler und `70` für unerwartete interne Fehler.
JSON-Modi verwenden die versionierten CLI-Envelopes.

## Implementierte CLI als Agenten-API

| Befehl | Zweck | Maschinenformat |
|---|---|---|
| `aidl check` | Compilerdiagnosen | JSON oder Human |
| `aidl ir` | Canonical IR | JSON-Envelope oder native kanonische IR |
| `aidl plan` | deterministischer Plan | JSON-Envelope oder native kanonische Ausgabe |
| `aidl diff` | IR-Diff, Klassifikation, Migrationshinweise | JSON oder Human |
| `aidl inspect <FQN>` | kompakte Deklarationsinspektion | JSON oder Human |
| `aidl dependencies <FQN>` | direkte und transitive Deklarationsabhängigkeiten | JSON; Human bleibt direkte Kompaktansicht |
| `aidl explain <FQN>` | vorhandene Diagnoseevidenz und erlaubte Fixes | JSON oder Human |
| `aidl summary` | begrenzte Projektzusammenfassung | JSON oder Human |
| `aidl impact <FQN>` | begrenzte Change-Impact-Evidenz | JSON oder Human |
| `aidl resolve` | Quellreferenz auflösen | JSON |
| `aidl complete` | compiler-owned Completion | JSON |
| `aidl document` | Deklarations-/Diagnosedokumentation | JSON |
| `aidl usages` | semantische Verwendungen | JSON |
| `aidl rename` | sicheren Rename planen/anwenden | JSON |

Nicht registriert sind derzeit unter anderem `aidl describe`, `aidl edit`,
`aidl build`, `aidl test`, `aidl graph`, `aidl simulate`,
`aidl compatibility`, `aidl migrate` und `aidl deploy`. Solche Namen in der
breiteren Sprachspezifikation dürfen nicht als vorhandene Agenten-API behandelt
werden.

## Abhängigkeits- und Kontextgrenzen

`aidl dependencies <FQN> --format json` verwendet ausschließlich die bereits
compiler-/Canonical-IR-owned Deklarations-ID-Relation. Es trennt direkte
`dependencies` von `transitiveDependencies`, ist zyklussicher und begrenzt
beide Listen unabhängig auf 128 Einträge; vollständige Counts und
Truncation-Flags bleiben erhalten. Details stehen in `docs/m8-dependencies.md`.

`summary`, `explain` und `impact` sind ebenfalls bewusst begrenzte
Projektionen. Agenten sollen diese APIs nutzen, statt aus Dateinamen oder
Quelltext neue semantische Beziehungen abzuleiten.

## Bearbeitung und generierte Dateien

Die AIDL-CLI besitzt keinen allgemeinen `edit`-Befehl. Quelländerungen werden
mit dem jeweiligen Editor/Patchmechanismus durchgeführt und anschließend vom
Compiler validiert.

Generierte Dateien sind keine manuellen Reparaturziele. Der aktuell belegte
M4-TypeScript/Fastify/PostgreSQL-Pfad verwendet repository-interne Generatoren
und Ownership-Marker; ein produktiver `aidl build`-Subcommand oder ein
installierter Generatorvertrag existiert noch nicht. Das M9-04-Wheel paketiert
den Compiler/CLI-Vertrag und die maschinenlesbaren `spec/*.json`-Daten, nicht
diesen repository-internen M4-Generatorpfad als neue Produktoberfläche.

## Versionsverträge für Agenten

Für maschinenlesbare Ausgaben gelten getrennte Versionsdomänen:

- Canonical IR `0.3.0` mit Schema-ID
  `https://aidl.example/spec/0.3/ir.schema.json`;
- aktuelles CLI-JSON-Schema `7.0.0` mit Schema-ID
  `https://aidl.example/spec/cli/7/cli-output.schema.json`; eingefrorene ältere
  CLI-Schemas bleiben separat gültig;
- `spec/profile-registry.json` trägt `registryVersion` `0.3.0`, während jedes
  Profil unabhängig seinen Major (aktuell `1`) besitzt.

Die installierte Distribution `aidl-toolchain` trägt für die M9-04 lokale
Packaging-Baseline `0.0.0`. Diese Versionsdomäne ist weder ein veröffentlichtes
Release noch ein Alias für IR-, CLI-Schema- oder Profilversionen.

Die `https://aidl.example/...` Identifier sind Repository-Vertragsidentitäten;
sie implizieren noch keinen veröffentlichten Download- oder Release-Endpunkt.

## Verbote für Coding-Agenten

- generierte Dateien direkt ändern,
- unbekannte Schlüssel, Befehle oder Bibliotheken erfinden,
- Profile oder Compilerregeln deaktivieren, um Fehler zu umgehen,
- compiler-owned Resolution durch PSI-/Textheuristiken ersetzen,
- öffentliche Schreiboperationen ohne Auth-/Idempotenzvertrag erzeugen,
- Service-Ownership durch direkten Store-Zugriff umgehen,
- Event-Consumer ohne Deduplizierung erzeugen,
- externe Effekte als exactly-once bezeichnen,
- Offline-Konflikte stillschweigend mit Client-Uhrzeit lösen,
- Secrets oder sensible Beispieldaten einbetten,
- destruktive Migrationen ohne belegte Kompatibilitäts-/Migrationsanalyse erzeugen.
