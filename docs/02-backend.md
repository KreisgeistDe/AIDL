# 2. Backend-DSL

## API-Surfaces

Eine Operation wird nicht allein durch service.exposes öffentlich. exposes
definiert den logischen Servicevertrag; eine api-Deklaration bestimmt die
externe Transportoberfläche.

~~~dsl
api PetstoreApi {
  transport rest
  version 1
  basePath "/api/v1"
  operations [
    query listAvailablePets,
    query getPet,
    mutation requestAdoption
  ]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 300 per 1m burst 50
}
~~~

Unterstützte Transporte sind rest, rpc und graphql. Topics/Queues werden über
Async-Verträge, Channels über realtime und Sync-Endpunkte über das
offline-Profil generiert.

Regeln:

- Interne Operationen sind ohne api-Zuordnung nicht extern erreichbar.
- Jede Surface besitzt Major-Version und Kompatibilitätsmodus.
- Rate Limits nennen Schlüssel, Fenster und Burst.
- Transportstatus und Wire-Namen werden aus typisierten Fehlern abgeleitet.
- Generatoren erzeugen einen schema-identischen Client für jede Zielplattform.
- GraphQL darf Nullbarkeit, Fehler und Paging nicht anders interpretieren als
  REST/RPC.
- Breaking Changes erfordern eine neue API-Major-Version.

## Operationsvertrag

Queries, Mutationen, Tasks und Workflows deklarieren Authentisierung,
Autorisierung, mögliche Fehler, Effects, Budgets und Retry-Verhalten. Öffentliche
Operationen erhalten daraus einen vollständigen Transportvertrag.

## Queries

Queries sind seiteneffektfrei, standardmäßig begrenzt und dürfen nur Daten lesen,
die dem ausführenden Service gehören oder über eine deklarierte Projektion
vorliegen.

~~~dsl
query listAvailablePets(
  filter: PetFilter,
  page: PageInput
) -> Page<PetSummary> {
  auth: public
  read: Pet.where(status == available)
           .filter(filter)
           .sort(createdAt desc)
           .page(page)
  consistency: strong
  cache: public ttl 30s vary [filter, page]
  errors: [InvalidPage]
  timeout: 2s
}
~~~

Jede Collection-Query MUSS ein Limit oder einen Page-/Stream-Vertrag besitzen.
Konsistenz ist strong, boundedStaleness(max: duration), session oder eventual.

## Mutationen

Jede Mutation MUSS auth, allow, errors und Idempotenz deklarieren. auth: public
benötigt eine publicReason-Annotation.

~~~dsl
mutation renamePet(input: RenamePetInput) -> Pet {
  auth: authenticated
  allow: canManagePet(input.petId)
  errors: [PetNotFound, ConcurrentChange, InvalidInput]
  idempotency:
    key input.operationId
    scope principal.subjectId
    retain 24h

  transaction on PetstoreDb isolation readCommitted {
    pet = Pet.require(input.petId) else PetNotFound
    write: pet.update(name: input.name)
      expect revision input.expectedRevision
      else ConcurrentChange
    return pet
  }

  audit: required
  timeout: 3s
}
~~~

Der Idempotenzspeicher bindet Schlüssel, Scope, normalisierte Eingabe,
Ergebnis oder öffentlichen Fehler und Ablaufzeit atomar. Derselbe Schlüssel mit
anderer Eingabe ergibt IdempotencyMismatch. Eine abgelaufene Speicherung darf
nicht als exactly-once-Garantie interpretiert werden.

Eine Mutation besitzt genau einen Root-Effect:

- eine lokale transaction,
- einen einzelnen idempotenten Resource-call,
- oder den Start eines Workflows beziehungsweise einer Saga.

Ein direkter Resource-call übernimmt sein Ergebnis als Mutationsergebnis:

~~~dsl
mutation beginUpload(input: BeginUploadInput)
  -> UploadSession<VideoObject> {
  auth: authenticated
  allow: canUpload(input.videoId)
  errors: [UnsupportedMedia, RateLimited]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 24h
  }
  call: VideoObjects.beginUpload(input)
  audit: required
  timeout: 3s
}
~~~

Der Resource-Adapter MUSS denselben Idempotenzschlüssel verwenden oder der
Compiler lehnt Retries ab.

## Serviceübergreifende Autorisierung

Eine Mutation darf vor ihrem Root-Effect eine explizite read-only
Remote-Autorisierung ausführen:

~~~dsl
authorize: remote query authorizeVideoUpload(
  input.videoId,
  principal.subjectId
) else NotAuthorized
~~~

Der Zielquery ist service-authentisiert, besitzt ein enges Timeout und darf
nicht schreiben. Ein Ausfall führt zu deny beziehungsweise einem deklarierten
DependencyUnavailable; er darf niemals stillschweigend erlauben.

Remote-Autorisierung ist kein Ersatz für eine verteilte Invariante. Muss ein
fremder Zustand bis zum Commit reserviert bleiben, ist eine Reservation oder
Saga erforderlich.

## Transaktionen und Nebenläufigkeit

Eine transaction umfasst genau einen transaktionalen Resource-Owner. Erlaubte
Isolationen sind readCommitted, repeatableRead und serializable. Der Adapter
MUSS die deklarierte Stufe nachweislich unterstützen oder den Build ablehnen.

Optimistische Writes verwenden expect revision. Die Prüfung und Änderung MUSS
ein atomarer Compare-and-set sein. Betroffene Invarianten werden nach allen
Writes und vor Commit geprüft.

~~~dsl
write: pet.update(status: pending)
  expect revision input.expectedPetRevision
  else ConcurrentChange
~~~

Nach einem erfolgreichen write wird die im Transaktionskontext gebundene
Entität auf den neuen Feldstand und die neue Revision aktualisiert. Flow-Typing
kennt unmittelbar gesetzte Non-null-Felder. Dadurch sind ein anschließendes
return View(entity) und Events mit diesen Feldern typisierbar. Bei Rollback
verfällt dieser lokale Stand.

Für pessimistische Sperren ist eine begrenzte Sperre explizit:

~~~dsl
pet = Pet.require(input.petId) lock update timeout 500ms
~~~

Cross-Service- oder Cross-Database-Transaktionen sind verboten. Dafür werden
Saga, Reservation oder kompensierende Operationen verwendet.

## Atomare Event-Publikation

Ein Event innerhalb einer Transaktion wird über via outbox publiziert. Runtime
persistiert State-Änderung und Outbox-Eintrag atomar. Zustellung bleibt
at-least-once; Consumer müssen deduplizieren.

~~~dsl
emit: AdoptionRequested(
  eventId: operationId(),
  requestId: request.id,
  occurredAt: now()
) to AdoptionEvents via outbox
~~~

Ein emit ohne via outbox ist innerhalb einer Transaktion ungültig. Ein Adapter
darf Outbox und Topic technisch zusammenführen, wenn die gleiche Semantik
beweisbar ist.

## Policies

~~~dsl
policy canManagePet(petId: Pet.id) -> bool {
  require principal.authenticated
  pet = Pet.require(petId)
  return principal.hasRole(admin)
      or principal.hasRole(shelterStaff, shelterId: pet.shelter.id)
}
~~~

Policies dürfen lokale Daten lesen, aber nicht schreiben, publizieren oder
Netzwerkzugriffe ausführen. Serviceübergreifende Autorisierung verwendet
signierte Claims oder explizite Authorize-Operationen; sie darf nicht heimlich
andere Datenbanken lesen.

## Events und Topics

~~~dsl
event AdoptionRequested version 1 {
  eventId: OperationId
  requestId: AdoptionRequest.id
  occurredAt: datetime
}

topic AdoptionEvents {
  events [AdoptionRequested]
  delivery atLeastOnce
  partition by requestId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}
~~~

Jedes Event besitzt eventId, occurredAt und eine explizite Schema-Version.
Topics deklarieren Delivery, Partitionierung, Ordering, Retention,
Kompatibilitätsmodus und Dead-Letter-Verhalten.

## Consumer

~~~dsl
consumer StartAdoptionReview
  on AdoptionRequested from AdoptionEvents {
  service PetstoreService
  idempotency: event.eventId retain 30d
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)
  start: workflow ReviewAdoption({ requestId: event.requestId })
}
~~~

Consumer werden at-least-once aufgerufen. Ohne Idempotenzklausel sind nur
nachweislich reine Consumer zulässig. Ordering gilt nur innerhalb der
deklarierten Partition.

Poison Events werden nach dem Retry-Budget in die Dead-Letter-Ablage
verschoben. Replay ist eine neue Delivery und verwendet denselben eventId.

## Projektionen

~~~dsl
projection PetSearch
  from [PetPublished, PetChanged]
  into PetSearchIndex {
  key event.petId
  map PetSearchDocument(
    id: event.petId,
    name: event.name,
    text: event.description
  )
  checkpoint perPartition
  rebuild replay
}
~~~

Eine Projektion besitzt Checkpoint-, Idempotenz- und Rebuild-Semantik.
eventual consistency ist am lesenden Query-Vertrag sichtbar.

rebuild replay nutzt die deklarierte Event-/Stream-Retention, rebuild snapshot
einen geprüften Projektion-Snapshot und rebuild from RESOURCE eine dauerhafte
kanonische Quelle. Reicht deren Retention nicht für einen vollständigen
Neuaufbau, meldet der Compiler AIDL-DIST432.

## Workflows und Sagas

~~~dsl
workflow ReviewAdoption(input: ReviewInput) -> AdoptionRequest {
  budget: duration 14d, attempts 8
  idempotency: input.requestId retain 30d

  step load retry none {
    request = query getAdoption(input.requestId)
  }

  approval shelterStaff {
    timeout: 10d
    onTimeout: fail ReviewTimeout
  }

  step decide retry exponential(max: 3) {
    result = mutation decideAdoption({
      operationId: workflow.stepId,
      requestId: input.requestId,
      expectedRevision: request.revision,
      decision: approval.decision,
      reason: approval.reason
    })
  }

  return result
}
~~~

Jeder Step besitzt eine stabile stepId. Wiederholte Steps müssen rein oder
idempotent sein.

onTimeout darf einen typisierten Fehler liefern oder eine idempotente Mutation,
Task beziehungsweise Workflow-Kompensation starten. Passt deren Ergebnis zum
Workflow-Output, beendet es den Timeout-Pfad erfolgreich; andernfalls muss ein
anschließender return- oder fail-Pfad explizit sein.

Eine Saga besteht aus lokal transaktionalen Schritten mit expliziter
Kompensation:

~~~dsl
saga ReserveAndBill(input: ReservationInput) -> Reservation {
  step reserve = mutation reserveInventory(input)
    compensate mutation releaseInventory(reserve.compensationToken)
  step charge = mutation chargePayment(input.payment)
    compensate mutation refundPayment(charge.paymentId)
  return Reservation(reserve, charge)
}
~~~

Kompensation bedeutet fachliche Gegenbuchung, nicht Rollback einer bereits
committeten fremden Transaktion.

## Tasks und Scheduler

~~~dsl
task GenerateThumbnail(input: ThumbnailInput) -> BlobHandle<ImageObject> {
  execution worker
  queue: ThumbnailJobs
  retry: exponential(max: 5)
  idempotency: input.assetId retain 7d
  resources: cpu 2cores, memory 2GB
  call: native media.thumbnail(input)
  errors: [UnsupportedMedia, ProcessingFailed]
  timeout: 10m
}

schedule CleanupExpiredUploads {
  cron "0 */6 * * *"
  timezone "UTC"
  singleton lease 20m
  start: task cleanupUploads()
}
~~~

Scheduler mit redundanten Instanzen verwenden eine Lease. Ein verpasster Lauf
deklariert catchUp none, latest oder all(max).

## Native Escape Hatch

~~~dsl
native function media.thumbnail {
  implementation: "./native/thumbnail.ts#thumbnail"
  input: ThumbnailInput
  output: BlobHandle<ImageObject>
  errors: [UnsupportedMedia, ProcessingFailed]
  effects: [blob.read, blob.write, cpu]
  capabilities: [blob:VideoObjects, blob:ThumbnailObjects]
  retrySafe: true
  deterministic: false
  budget: cpu 120s, memory 2GB
  timeout: 10m
}
~~~

Native Module erhalten ausschließlich deklarierte Capabilities. Secrets,
Netzwerk, Stores und Clock werden als eingeschränkte Handles injiziert.
Undeklarierter Zugriff ist ein Build- oder Laufzeitfehler.
