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

