# 11. Standardbibliothek

## Versionierung

Die Standardbibliothek aidl.std ist unabhängig von der Sprache versioniert und
im Lockfile fixiert. Implizite Imports sind auf die hier genannten
fundamentalen Typen beschränkt.

## Identität und Zeit

~~~dsl
opaque SubjectId = string(1..200)
opaque TenantId = string(1..200)
opaque DeviceId = uuid
opaque OperationId = uuid
opaque MessageId = uuid
opaque Cursor = string(1..2048)
~~~

Principal enthält:

- subjectId,
- authenticationLevel,
- roles und scopes,
- optional tenantId,
- issuedAt und expiresAt,
- serviceIdentity oder delegierte Useridentität.

Clock und RandomSource sind injizierte Effects. Tests können sie deterministisch
steuern.

operationId() erzeugt eine neue OperationId über RandomSource. Der Wert wird
bei UI-Retries, Workflow-Step-Retries und Event-Outbox-Retries persistiert und
nicht erneut ausgewertet. Event-IDs verwenden OperationId, wenn sie unmittelbar
als nachgelagerter Idempotenzschlüssel dienen; MessageId bleibt für reine
Transporthüllen verfügbar.

## Collections und Paging

~~~dsl
value PageInput {
  cursor: Cursor?
  size: int(min: 1, max: 200) default 20
}

value Page<T: serializable> {
  items: [T]
  nextCursor: Cursor?
  hasMore: bool
}

value OffsetPageInput {
  offset: int(min: 0) default 0
  size: int(min: 1, max: 200) default 20
}
~~~

Cursor-Paging ist Standard. Offset-Paging benötigt eine stabile Sortierung und
ist für stark veränderliche große Collections mit einer Warnung verbunden.

set<T: hashable> besitzt addWinsSet und removeWinsSet nur innerhalb eines
Sync-Vertrags; außerhalb bleibt es ein gewöhnlicher Value.

## Fehler

ErrorValue ist ein Compiler-Bound, kein frei implementierbares Runtime-Interface.

Standardfehler:

- InvalidInput mit typisierten FieldError-Einträgen,
- NotAuthenticated,
- NotAuthorized,
- NotFound,
- ConcurrentChange mit currentRevision,
- IdempotencyMismatch,
- RateLimited mit retryAfter,
- DependencyUnavailable,
- Timeout,
- InternalFailure mit correlationId,
- UpgradeRequired,
- SyncConflict und SyncRejected.

Öffentliche Operationen müssen konkrete nominale Fehler oder ausdrücklich
erlaubte Standardfehler nennen.

## Result und asynchrone Zustände

~~~dsl
union Result<T: serializable, E: ErrorValue> {
  success(value: T)
  failure(error: E)
}

union AsyncState<T: serializable, E: ErrorValue> {
  idle
  loading(previous: T?)
  ready(value: T, stale: bool)
  empty
  failed(error: E, previous: T?)
}
~~~

Transportgeneratoren dürfen Exceptions intern verwenden, müssen an der
öffentlichen Grenze aber den deklarierten Fehlervertrag erhalten.

## Idempotenz

~~~dsl
value IdempotencyContext {
  operationId: OperationId
  scope: string
  requestedAt: datetime
}
~~~

Eine Operation normalisiert ihre Eingabe nach Schema, bevor der Input-Hash
gebildet wird. Secrets und flüchtige Transportfelder sind ausgeschlossen.

## Medien

~~~dsl
value BlobHandle<S: serializable> {
  store: string
  key: string
  version: string
  sha256: string
  sizeBytes: int(min: 0)
  mediaType: string
  schema: string
}

value UploadSession<S: serializable> {
  id: uuid
  expiresAt: datetime
  chunkSizeBytes: int
  uploadedBytes: int
  status: UploadSessionStatus
}

value RenditionSet<S: serializable> {
  source: BlobHandle<S>
  renditions: map<string, BlobHandle<S>>
}

value DeliveryHandle<S: serializable> {
  cdn: string
  object: BlobHandle<S>
  policy: string
}
~~~

BlobHandle-Werte sind opak für Clients. Provider-URLs und Credentials sind
nicht Bestandteil des Handles.

DeliveryHandle ist ebenfalls stabil und credentialfrei. Ein API-/Frontend-
Adapter tauscht es pro autorisiertem Request gegen eine kurzlebige signierte
URL oder ein Cookie aus. Ablaufende URLs werden nie als Domänenzustand
persistiert.

beginUpload validiert Media Type, Größe und Quota, bindet die Idempotenz-ID und
liefert eine kurzlebige UploadSession. Der Client erhält nur auf den deklarierten
Store begrenzte Upload-Rechte. Ein beim Abschluss geliefertes BlobHandle wird
vom Serveradapter kryptografisch beziehungsweise providerseitig verifiziert.

## Sync

~~~dsl
value SyncOperation<P: serializable> {
  operationId: OperationId
  deviceId: DeviceId
  entityId: uuid
  baseRevision: revision?
  patch: P
  clientSchemaVersion: string
}

union SyncOutcome<T: serializable> {
  confirmed(value: T, revision: revision)
  merged(value: T, revision: revision)
  conflict(conflict: ConflictRecord<T>)
  rejected(error: SyncRejected)
  upgradeRequired(error: UpgradeRequired)
}

value SyncStatus<T: serializable> {
  online: bool
  syncing: bool
  pendingCount: int
  conflicts: [ConflictRecord<T>]
  rejected: [SyncRejected]
  error: ErrorValue?
  summary: string
}

value MergeInput<T: serializable> {
  base: T?
  local: T
  remote: T
  causality: Causality
}

union MergeDecision<T: serializable> {
  merged(value: T)
  manual(reason: string)
  rejected(code: string)
}
~~~

revision ist opak. Anwendungscode darf Revisionen auf Gleichheit prüfen, aber
nicht arithmetisch bearbeiten.

## Realtime

~~~dsl
value ChannelCursor {
  channelId: string
  cursor: Cursor
  issuedAt: datetime
}

union ConnectionState {
  connecting
  connected
  reconnecting(attempt: int)
  offline
  failed(error: DependencyUnavailable)
}
~~~

## UI

aidl.ui.std stellt semantische Komponenten bereit:

- Heading, Text, Image und Link,
- Button, Menu, Dialog und Alert,
- Form, Field, Select und ValidationSummary,
- List, Grid, Table und Pagination,
- Loading, Empty, Error und Conflict States,
- Upload, Progress und Sync Indicator.

Diese Komponenten sind keine visuelle Bibliothek. Themes und Plattformadapter
bestimmen die Darstellung unter Einhaltung von A11y und Design Tokens.

component<T> ist ein Compile-Zeit-Typ für reine Renderfunktionen. action ist ein
typisierter UI-Callback ohne direkten Store-/Netzwerkzugriff.

## Mengen- und Zeiteinheiten

Compiler normalisiert:

- Zeit: ms, s, m, h, d,
- Bytes: B, KB, MB, GB, TB,
- CPU-Kapazität: mCPU, core oder cores,
- Prozentsätze: 0% bis 100%.

Einheiten sind dimensionssicher; 5GB kann nicht mit 5s verglichen werden.
