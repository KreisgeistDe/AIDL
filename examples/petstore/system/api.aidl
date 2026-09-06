module petstore.system.api

import petstore.operations.pets.*
import petstore.operations.adoptions.*

export api PetstoreApi {
  transport rest
  version 1
  basePath "/api/v1"
  operations [
    query listAvailablePets,
    query getPet,
    mutation updatePetProfile,
    query getAdoption,
    query listMyAdoptions,
    mutation requestAdoption,
    mutation decideAdoption
  ]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 300 per 1m burst 50
}

