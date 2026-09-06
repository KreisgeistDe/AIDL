module petstore.domain.pets

export enum Species { dog, cat, rabbit, bird, other }
export enum PetStatus { available, pending, adopted }

export value PetImage {
  url: url required
  alt: string(1..180) required
}

export value PetFilter {
  species: Species?
  minimumAgeMonths: int(min: 0)?
  maximumAgeMonths: int(min: 0)?
  shelterId: Shelter.id?

  invariant validRange:
    minimumAgeMonths == null
    or maximumAgeMonths == null
    or minimumAgeMonths <= maximumAgeMonths
}

export value UpdatePetProfileInput {
  operationId: OperationId required
  petId: Pet.id required
  expectedRevision: revision required
  name: string(1..80) required
  ageMonths: int(min: 0, max: 480) required
  shortDescription: string(1..300) required
  description: string(1..4000) required
  primaryImage: PetImage required
}

export entity Shelter {
  id: uuid primary generated immutable
  revision: revision generated concurrencyToken
  name: string(1..120) required mutable
  city: string(1..120) required mutable
  email: email required mutable sensitive
  pets: [Pet] via shelter
}

export entity Pet {
  id: uuid primary generated immutable
  revision: revision generated concurrencyToken
  name: string(1..80) required mutable
  species: Species required immutable
  ageMonths: int(min: 0, max: 480) required mutable
  shortDescription: string(1..300) required mutable
  description: string(1..4000) required mutable
  primaryImage: PetImage required mutable
  status: PetStatus default available mutable
  shelter: ref Shelter required immutable onDelete restrict
  adoptedAt: datetime? mutable
  createdAt: datetime generated immutable

  index byCatalog(status, species, createdAt desc)
  invariant adoptionTimestamp:
    (status == adopted and adoptedAt != null)
    or (status != adopted and adoptedAt == null)
}

export view PetSummary from Pet {
  id
  revision
  name
  species
  ageMonths
  shortDescription
  primaryImage
  status
  shelter { id, name, city }
}

export view PetDetails from Pet {
  id
  revision
  name
  species
  ageMonths
  shortDescription
  description
  primaryImage
  status
  adoptedAt
  createdAt
  shelter { id, name, city }
}

