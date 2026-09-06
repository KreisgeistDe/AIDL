module petstore.system.topology

import petstore.domain.pets.*
import petstore.domain.adoptions.*
import petstore.contracts.adoption-events.AdoptionEvents
import petstore.operations.pets.*
import petstore.operations.adoptions.*
import petstore.system.resources.PetstoreDb
import petstore.system.api.PetstoreApi

export service PetstoreService {
  owns [Shelter, Pet, AdoptionRequest]
  uses [PetstoreDb, AdoptionEvents]
  exposes [
    query listAvailablePets,
    query getPet,
    mutation updatePetProfile,
    query getAdoption,
    query listMyAdoptions,
    mutation requestAdoption,
    mutation decideAdoption,
    mutation expireAdoption
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
  telemetry inherit
}

export system PetstoreSystem {
  services [PetstoreService]
  resources [PetstoreDb, AdoptionEvents]
  apis [PetstoreApi]
}
