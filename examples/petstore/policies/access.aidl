module petstore.policies.access

import petstore.domain.pets.*
import petstore.domain.adoptions.*

export policy canManagePet(petId: Pet.id) -> bool {
  require principal.authenticated
  pet = Pet.byId(petId)
  return pet != null
      and (
        principal.hasRole(admin)
        or principal.hasRole(
          shelterStaff,
          shelterId: pet.shelter.id
        )
      )
}

export policy canReadAdoption(id: AdoptionRequest.id) -> bool {
  require principal.authenticated
  request = AdoptionRequest.byId(id)
  return request != null
      and (
        principal.hasRole(admin)
        or request.applicantId == principal.subjectId
        or principal.hasRole(
          shelterStaff,
          shelterId: request.pet.shelter.id
        )
      )
}

export policy canDecideAdoption(id: AdoptionRequest.id) -> bool {
  require principal.authenticated
  request = AdoptionRequest.byId(id)
  return request != null
      and (
        principal.hasRole(admin)
        or principal.hasRole(
          shelterStaff,
          shelterId: request.pet.shelter.id
        )
      )
}

