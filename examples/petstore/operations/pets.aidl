module petstore.operations.pets

import petstore.domain.pets.*
import petstore.domain.errors.*
import petstore.policies.access.canManagePet
import petstore.system.resources.PetstoreDb

@publicReason("Der Tierkatalog ist öffentlich sichtbar.")
export query listAvailablePets(
  filter: PetFilter default {},
  page: PageInput default { size: 12 }
) -> Page<PetSummary> {
  auth: public
  read: Pet.where(status == available)
           .filter(filter)
           .sort(createdAt desc)
           .page(page)
           .project(PetSummary)
  consistency: strong
  cache: public ttl 30s vary [filter, page]
  errors: [InvalidInput, InternalFailure]
  timeout: 2s
}

@publicReason("Öffentliche Detailseite eines vermittelbaren Tiers.")
export query getPet(id: Pet.id) -> PetDetails? {
  auth: public
  read: Pet.byId(id).project(PetDetails)
  consistency: strong
  cache: public ttl 30s vary [id]
  errors: [InternalFailure]
  timeout: 2s
}

export mutation updatePetProfile(
  input: UpdatePetProfileInput
) -> PetDetails {
  auth: authenticated
  allow: canManagePet(input.petId)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    PetNotFound,
    ConcurrentChange,
    InvalidInput,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 24h
  }

  transaction on PetstoreDb isolation readCommitted {
    pet = Pet.require(input.petId) else PetNotFound
    write: pet.update(
      name: input.name,
      ageMonths: input.ageMonths,
      shortDescription: input.shortDescription,
      description: input.description,
      primaryImage: input.primaryImage
    )
      expect revision input.expectedRevision
      else ConcurrentChange
    return PetDetails(pet)
  }

  audit: required
  timeout: 3s
}

