module petstore.m4

app PetstoreApp {
  profile core version 1
  profile distributed version 1
  profile cloud version 1
  system PetstoreSystem
  api PetstoreApi
  defaultDeployment local
}

auth {
  provider oidc config("ISSUER")
  subject claim "sub" as SubjectId
  roles [user]
  scopes [pets.write]
  serviceIdentities required
}

export value CreatePetInput {
  operationId: uuid required
  id: uuid required
  name: string(1..80) required
}

export entity RunnablePet {
  id: uuid primary immutable
  revision: revision generated concurrencyToken
  name: string(1..80) required mutable
}

export event RunnablePetCreated version 1 {
  eventId: OperationId required
  petId: uuid required
  occurredAt: datetime required
}

export topic RunnablePetEvents {
  events [RunnablePetCreated]
  delivery atLeastOnce
  partition by petId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}

export mutation createPet(input: CreatePetInput) -> RunnablePet {
  auth: authenticated
  allow: true
  errors: []
  idempotency: "petstore-create" retain 1d
  transaction on PetstoreDb isolation readCommitted {
    pet = RunnablePet.create(id: input.id, name: input.name)
    emit: RunnablePetCreated(eventId: operationId(), petId: pet.id, occurredAt: now()) to RunnablePetEvents via outbox
    return pet
  }
}

export api PetstoreApi {
  transport rest
  version 1
  operations [mutation createPet]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 300 per 1m burst 50
}

export resource PetstoreDb sql {
  consistency strong
  transactions [readCommitted]
  migrations expandBackfillContract
  encryption required
}

export service PetstoreService {
  owns [RunnablePet]
  uses [PetstoreDb, RunnablePetEvents]
  exposes [mutation createPet]
  runs []
  reliability {
    idempotencyStore PetstoreDb
  }
}

export system PetstoreSystem {
  services [PetstoreService]
  resources [PetstoreDb, RunnablePetEvents]
  apis [PetstoreApi]
}

export deployment local for PetstoreSystem {
  environment development
  target process
  colocate services all
  bind PetstoreDb container "postgres:17"
  bind RunnablePetEvents memory
}
