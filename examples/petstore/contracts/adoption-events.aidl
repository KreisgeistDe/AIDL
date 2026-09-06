module petstore.contracts.adoption-events

import petstore.domain.pets.Pet
import petstore.domain.adoptions.AdoptionRequest

export event AdoptionRequested version 1 {
  eventId: OperationId required
  requestId: AdoptionRequest.id required
  petId: Pet.id required
  occurredAt: datetime required
}

export topic AdoptionEvents {
  events [AdoptionRequested]
  delivery atLeastOnce
  partition by requestId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}
