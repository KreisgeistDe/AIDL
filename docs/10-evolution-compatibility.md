# 10. Evolution und Kompatibilität

## Unabhängige Versionen

Folgende Artefakte werden unabhängig versioniert:

- Sprache und Profile,
- Anwendungsrelease,
- öffentliche API,
- Event-Schema,
- Sync-Protokoll,
- persistiertes Schema,
- native Adapter,
- Deployment-Adapter.

Eine app-Version ersetzt keine dieser Kompatibilitätsangaben.

## Quellsprachversion und M16.5-Migration

M16.5/E2 legt für spätere experimentelle Normalisierungen einen zusätzlichen,
nicht-normativen Migrationsvertrag fest. Die vollständige Entscheidung steht in
`docs/m16-5-e2-compatibility-migration-contract.md`; sie ändert keine heute
akzeptierte Syntax.

Eine normale Kompilation erhält genau **eine explizite Quellsprachversion** aus
Projekt-/Compiler-Konfiguration, bevor AIDL-Quelltext geparst wird. Sie wird
nicht aus Dateiinhalten geraten, nicht pro Datei gewählt und nicht mit app-,
Profil-, API-, Event- oder Datenmigrationsversionen gleichgesetzt. Ein
Importgraph mit unterschiedlichen Quellsprachversionen wird vor der
semantischen Analyse abgewiesen.

Ein späterer Syntax-Migrator arbeitet dagegen mit zwei getrennten,
unveränderlichen Kompilationskontexten: alter Quelltext unter alter
Quellsprachversion und Kandidat unter Zielversion. Für eine rein syntaktische
Migration müssen beide semantisch auf kompatible Canonical IR abbilden. Das
Hinzufügen einer weiteren akzeptierten Schreibweise ist `expandable`, ein
projektweiter Versionswechsel mit deterministischer Umschreibung ist
`coordinated`, und das Entfernen einer zuvor akzeptierten Schreibweise ist
`breaking`. Ein vorhandener Migrator macht das Entfernen alter Syntax nicht
`compatible`.

Formatter und Migrator sind getrennt: Ein Formatter kanonisiert nur innerhalb
der bereits gewählten Quellsprachversion; nur ein expliziter Migrator darf
einen Versionswechsel planen. Unveränderte Bereiche müssen byte-identisch
bleiben, semantisch geordnete Sequenzen dürfen nicht umsortiert werden, und
eine Migration scheitert geschlossen bei veralteten Quell-/Schema-Fingerprints,
überlappenden oder mehrdeutigen Ankern oder einem nicht kompatiblen
semantischen Diff.

## Semantischer Diff

aidl plan und aidl compatibility klassifizieren jede Änderung:

| Klasse | Bedeutung |
|---|---|
| compatible | ohne Koordination ausrollbar |
| expandable | zunächst additive Expand-Phase nötig |
| coordinated | Produzent und Konsument benötigen überlappende Versionen |
| breaking | explizite Migration oder neues Major erforderlich |
| dataLoss | gesonderte Bestätigung und Wiederherstellungsplan nötig |

Textuell unterschiedliche, semantisch gleiche Formatierung erzeugt keinen Diff.

## API-Kompatibilität

Standardmäßig kompatibel:

- neues optionales Input-Feld mit Default,
- neues Output-Feld,
- neuer deklarierter Fehler nur in neuer API-Major-Version oder wenn der
  Clientvertrag unknown errors erlaubt.

Standardmäßig breaking:

- Entfernen oder Umbenennen eines Feldes,
- engerer Input-Constraint,
- weiterer null-Wert im Output,
- Änderung von Auth, Konsistenz oder Idempotenz,
- Änderung eines stabilen Error Codes.

## Event-Kompatibilität

Events sind immutable. Eine neue Version erhält eine neue Schema-Version.

~~~dsl
event VideoPublished version 2
  evolves VideoPublished version 1 {
  videoId: Video.id
  channelId: Channel.id
  title: string
  visibility: Visibility default public
}

upcast VideoPublished 1 -> 2 {
  visibility: public
}
~~~

Upcaster sind rein und deterministisch. Consumer deklarieren akzeptierte
Versionen. Ein Topic im backward-Modus darf keine nicht upcastbare alte
Nachricht verlieren.

## Datenbankschema

Zero-Downtime-Migrationen folgen:

1. expand: additive Spalten, Tabellen, Indizes oder Dual-Read-Fähigkeit,
2. deployReaders: neue Version kann altes und neues Schema lesen,
3. backfill: resumierbarer, idempotenter Job mit Checkpoint,
4. switchWrites: neue kanonische Schreibweise,
5. verify: Invarianten und Zähler vergleichen,
6. contract: alte Darstellung nach Kompatibilitätsfenster entfernen.

~~~dsl
migration AddPetMicrochip from "0.2" to "0.3" {
  expand add Pet.microchipId nullable
  backfill task InferMicrochipBatch checkpoint Pet.id
  verify query petsMissingMicrochip <= acceptedUnknown
  contract after 30d make Pet.microchipId required
  rollback until switchWrites
}
~~~

Destruktive Schritte benötigen breaking change, Backup-/Restore-Nachweis und
explizite Datenverlustklassifikation.

## Projektionen und Suchindizes

Mappings werden mit einer Projection-Version versehen. Inkompatible Änderungen
erzeugen einen parallelen Zielindex:

1. neuen Index erstellen,
2. Eventlog replayen,
3. Lag und Stichproben prüfen,
4. Alias atomar umschalten,
5. alten Index nach Rollbackfenster entfernen.

## Offline-Clients

Jede Sync-Änderung prüft:

- minimale und maximale Clientversion,
- Lesbarkeit neuer Serverfelder,
- Upcast alter Operationen,
- Tombstone-Watermark,
- Full-Resync-Bedarf,
- Verhalten bei abgelaufener Clientversion.

Server dürfen alte Clients nur mit einem typisierten UpgradeRequired-Ergebnis
abweisen. Lokal ungesyncte Daten müssen exportierbar oder migrierbar bleiben.

## Rolling Deployments

Während eines Rolling Deployments müssen gleichzeitig aktive Versionen
kompatibel sein. Der Plan berücksichtigt:

- API-Produzent/Konsument,
- Event-Produzent/Konsument,
- Store-Reader/Writer,
- Workflow-Schritte älterer Instanzen,
- Idempotenz-Key-Format,
- Cache- und Projektion-Schema.

Ein Deployment mit maxUnavailable 0 wird abgelehnt, wenn eine Migration ein
exklusives inkompatibles Schemafenster verlangt.

## Entfernen von Verträgen

Öffentliche Felder, Events und Operationen durchlaufen:

deprecated -> usageObservedZero -> disabled -> removed.

Die Beobachtungsdauer und Telemetriequelle werden deklariert. Fehlende
Telemetriedaten dürfen nicht als Nullnutzung interpretiert werden.
