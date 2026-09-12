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
  field id: uuid primary generated immutable
  field revision: revision generated concurrencyToken
  field name: string(1..120) required mutable
  field city: string(1..120) required mutable
  field email: email required mutable sensitive
  field pets: [Pet] via shelter
}

export entity Pet {
  field id: uuid primary generated immutable
  field revision: revision generated concurrencyToken
  field name: string(1..80) required mutable
  field species: Species required immutable
  field ageMonths: int(min: 0, max: 480) required mutable
  field shortDescription: string(1..300) required mutable
  field description: string(1..4000) required mutable
  field primaryImage: PetImage required mutable
  field status: PetStatus default available mutable
  field shelter: ref Shelter required immutable onDelete restrict
  field adoptedAt: datetime? mutable
  field createdAt: datetime generated immutable

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

