module fixtures.valid.m4minimal

app SnapshotApp {
  profile core version 1
  profile distributed version 1
  profile cloud version 1
  system SnapshotSystem
  api SnapshotApi
  defaultDeployment local
}

auth {
  provider oidc config("ISSUER")
  subject claim "sub" as SubjectId
  roles [user]
  scopes [items.write]
  serviceIdentities required
}

export value CreateItemInput {
  operationId: uuid required
  id: uuid required
  name: string(1..80) required
}

export entity SnapshotItem {
  id: uuid primary immutable
  revision: revision generated concurrencyToken
  name: string(1..80) required mutable
}

export event SnapshotItemCreated version 1 {
  eventId: OperationId required
  itemId: uuid required
  occurredAt: datetime required
}

export topic SnapshotItemEvents {
  events [SnapshotItemCreated]
  delivery atLeastOnce
  partition by itemId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}

export mutation createItem(input: CreateItemInput) -> SnapshotItem {
  auth: authenticated
  allow: true
  errors: []
  idempotency: "snapshot-create" retain 1d
  transaction on SnapshotDb isolation readCommitted {
    item = SnapshotItem.create(id: input.id, name: input.name)
    emit: SnapshotItemCreated(eventId: operationId(), itemId: item.id, occurredAt: now()) to SnapshotItemEvents via outbox
    return item
  }
}

export api SnapshotApi {
  transport rest
  version 1
  operations [mutation createItem]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 300 per 1m burst 50
}

export resource SnapshotDb sql {
  consistency strong
  transactions [readCommitted]
  migrations expandBackfillContract
  encryption required
}

export service SnapshotService {
  owns [SnapshotItem]
  uses [SnapshotDb, SnapshotItemEvents]
  exposes [mutation createItem]
  runs []
  reliability {
    idempotencyStore SnapshotDb
  }
}

export system SnapshotSystem {
  services [SnapshotService]
  resources [SnapshotDb, SnapshotItemEvents]
  apis [SnapshotApi]
}

export deployment local for SnapshotSystem {
  environment development
  target process
  colocate services all
  bind SnapshotDb container "postgres:17"
  bind SnapshotItemEvents memory
}
