# 7. Verteilte Systeme

## System und Services

~~~dsl
system PetstoreSystem {
  services [PetstoreService]
  resources [PetstoreDb, AdoptionEvents]
}

service PetstoreService {
  owns [Shelter, Pet, AdoptionRequest]
  uses [PetstoreDb, AdoptionEvents]
  exposes [
    query listAvailablePets,
    query getPet,
    mutation requestAdoption
  ]
  runs [
    consumer StartAdoptionReview,
    workflow ReviewAdoption
  ]
  reliability {
    idempotencyStore PetstoreDb
    inboxStore PetstoreDb
    workflowStore PetstoreDb
  }
}
~~~

Ein Service ist:

- Ownership-Grenze für Entitäten,
- Transaktionsgrenze,
- Versionierungs- und Deployment-Komponente,
- Identität für Service-to-Service-Policies.

Der reliability-Block bindet Runtime-Zustand explizit:

| Property | Inhalt |
|---|---|
| idempotencyStore | Schlüssel, Input-Hash, Ergebnis und Retention |
| inboxStore | Consumer-Claims und Deduplizierung |
| workflowStore | Steps, Timer, Approvals und Kompensationen |
| projectionStore | Checkpoints und Rebuild-Generation |
| syncStore | Operation-Dedupe, Cursor und kanonische Revisionen |

Alle redundanten Instanzen eines Services müssen denselben logisch
konsistenten Reliability-Store sehen. Ein In-Memory-Binding ist ausschließlich
in lokalen Deployments zulässig.

Ein Modul bleibt ausschließlich Namespace und Compile-Zeit-Struktur.

## Ownership-Regeln

1. Jede persistierte Entität MUSS genau einen Service-Owner besitzen.
2. Nur der Owner darf den zugrunde liegenden Store direkt verwenden.
3. ref darf die Owner-Grenze nicht überschreiten.
4. Andere Services verwenden nominale IDs, unveränderliche Snapshots,
   öffentliche Operationen oder Events.
5. Ein import einer fremden Entität erteilt keinen Lese- oder Schreibzugriff.
6. Eine Invariante darf nur Daten derselben lokalen Transaktionsgrenze umfassen.

Der Compiler baut einen Datenzugriffsgraph und lehnt versteckte Shared-Database-
Kopplung ab.

Services dürfen neben Consumer, Workflow, Task und Schedule auch projection,
sync und channel ausführen. Ein Service ohne eigene Entitäten ist für Search,
Gateway oder Stream Processing zulässig, sofern alle verwendeten Ressourcen
explizit genannt sind.

## Synchrone Service-Aufrufe

~~~dsl
client CatalogClient for CatalogService {
  call getVideo {
    timeout 800ms
    retry exponential(max: 2) when [Unavailable, Timeout]
    circuitBreaker openAfter 20 failures window 30s
    bulkhead maxConcurrent 200
  }
}
~~~

Retries sind nur für reine Queries oder idempotente Mutationen zulässig.
Timeouts umfassen die gesamte Operation, nicht jeden Retry einzeln, sofern
kein attemptTimeout angegeben ist.

Eine synchrone Aufrufkette besitzt ein Compilerbudget für maximale Tiefe,
Latenz und Fan-out. Zyklen im synchronen Servicegraph sind ungültig.

## Asynchrone Kommunikation

Events sind Fakten in Vergangenheitsform. Commands an Queues sind
Arbeitsaufträge. Topics verteilen an unabhängige Consumer Groups; Queues
verteilen innerhalb einer Worker Group.

~~~dsl
queue TranscodeJobs {
  messages [TranscodeVideo]
  delivery atLeastOnce
  visibilityTimeout 15m
  deadLetter after 5 attempts
}
~~~

Jede Nachricht besitzt messageId/eventId und occurredAt/enqueuedAt.
atMostOnce ist nur mit explicitDataLossAcceptance zulässig. exactlyOnce ist
kein erlaubter verteilter Delivery-Wert.

## Ordering und Partitionierung

ordering perPartition verlangt partition by EXPRESSION. Globales Ordering ist
nur für explizit begrenzte Streams erlaubt und benötigt ein Throughput-Budget.

Consumer dürfen Reihenfolge ausschließlich innerhalb eines Partition Keys
annehmen. Replays und Dead-Letter-Wiederaufnahme behalten ID und Partition Key.

## Deduplizierung

Ein Consumer-Idempotenzvertrag speichert mindestens:

- Consumer-ID und Schema-Version,
- Message-ID,
- Status processing, completed oder failedFinal,
- Ablaufzeit,
- optional Ergebnis-/Side-Effect-Referenzen.

Die Claim- und Commit-Operation wird mit lokalen Writes atomar verbunden oder
verwendet Inbox plus Outbox. Externe APIs benötigen eigene Idempotenzschlüssel
oder eine fachliche Reconciliation.

## Konsistenz

Der lesende Vertrag deklariert eine der folgenden Stufen:

| Stufe | Bedeutung |
|---|---|
| strong | Commit ist beim anschließenden Read sichtbar |
| session | eigene bestätigte Änderungen sind in derselben Session sichtbar |
| boundedStaleness | maximale bekannte Verzögerung |
| eventual | Konvergenz ohne feste Zeitgrenze |

Cross-Service-Read-Models sind projection und mindestens eventual. UI und
öffentliche API dürfen diese Eigenschaft nicht verstecken.

## CQRS und Projektionen

Projektionen konsumieren versionierte Events und schreiben ausschließlich in
ihren deklarierten Zielstore. Sie besitzen:

- deterministische Mapping-Funktion,
- Checkpoint je Partition,
- Deduplizierung,
- Rebuild aus Replay oder Snapshot,
- maximal erlaubte Lag,
- Schema- und Alias-Migrationsplan.

Ein Query gegen eine Projektion nennt deren Konsistenz und Verhalten bei
Rebuild.

## Sagas und Reservations

Verteilte Invarianten werden als Prozess modelliert:

1. lokale Reservation mit Ablaufzeit,
2. Event oder idempotenter Command,
3. lokale Bestätigung,
4. Kompensation bei endgültigem Fehler.

Eine Saga MUSS für jeden bereits committenden, fachlich reversiblen Step eine
Kompensation oder explicitIrreversible-Begründung deklarieren. Kompensationen
sind selbst idempotent.

## Redundante Ausführung

Horizontale Replikation ist sicher, wenn:

- Request-State außerhalb des Prozesses liegt,
- Mutationen Idempotenz und Concurrency deklarieren,
- Scheduler Singleton-Leases besitzen,
- Consumer Inbox/Idempotenz verwenden,
- Workflow-Steps stabile IDs besitzen,
- Sessions in signierten Tokens oder einem gemeinsamen Store liegen.

In-Memory-Singletons, lokale Cron-Jobs und nicht persistierte Retry-Zähler sind
im distributed-Profil verboten.

## Realtime Channels

~~~dsl
channel LiveComments<Message: serializable> {
  transport websocket
  delivery atLeastOnce
  ordering perConnection
  resume cursor
  backpressure dropOldest(maxBuffered: 100)
  auth authenticated
  fallback query listComments
}
~~~

Channels deklarieren Transportklasse, Resume, Backpressure, Auth und Fallback.
WebSocket, Server-Sent Events und Push sind Adapter; die fachliche Semantik
bleibt transportneutral.

## Mandantenfähigkeit

~~~dsl
tenant model Organization {
  key organizationId
  isolation row
  require principal.organizationId
  encryptionKey perTenant
  export supported
  erase supported
}
~~~

Isolationen sind row, schema, database oder deployment. Jede Query, Mutation,
Projektion, Cache- und Topic-Partition muss den Tenant Key propagieren. Der
Compiler lehnt Cache Keys und Events ohne benötigten Tenant-Kontext ab.

## Serviceidentitäten

Service-to-Service-Aufrufe verwenden servicePrincipal. Rollen eines Endnutzers
werden nur als signierte Delegation mit Audience und Ablaufzeit weitergegeben.
Ein Service darf ungeprüfte Client-Claims nicht transitiv vertrauen.
