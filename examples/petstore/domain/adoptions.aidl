module petstore.domain.adoptions

import petstore.domain.pets.Pet

export enum AdoptionStatus {
  submitted,
  reviewing,
  approved,
  rejected,
  expired,
  withdrawn
}

export enum AdoptionDecision { approved, rejected }

export value AdoptionRequestInput {
  operationId: OperationId required
  petId: Pet.id required
  expectedPetRevision: revision required
  fullName: string(2..120) required
  email: email required
  motivation: string(30..2000) required
  acceptedTerms: bool(equals: true) required
}

export value AdoptionDecisionInput {
  operationId: OperationId required
  requestId: AdoptionRequest.id required
  expectedRevision: revision required
  decision: AdoptionDecision required
  reason: string(1..1000) required
}

export value ReviewInput {
  requestId: AdoptionRequest.id required
}

export value ExpireAdoptionInput {
  operationId: OperationId required
  requestId: AdoptionRequest.id required
}

export entity AdoptionRequest {
  field id: uuid primary generated immutable
  field revision: revision generated concurrencyToken
  field pet: ref Pet required immutable onDelete restrict
  field applicantId: SubjectId required immutable
  field applicantName: string(2..120) required immutable sensitive
  field applicantEmail: email required immutable sensitive
  field status: AdoptionStatus default submitted mutable
  field motivation: string(30..2000) required immutable sensitive
  field termsAcceptedAt: datetime required immutable
  field decisionReason: string(1..1000)? mutable
  field createdAt: datetime generated immutable
  field decidedAt: datetime? mutable

  index byApplicant(applicantId, createdAt desc)
  index byPet(pet, createdAt desc)
  invariant decisionComplete:
    status not in [approved, rejected, expired]
    or (decidedAt != null and decisionReason != null)
}

export view AdoptionRequestSummary from AdoptionRequest {
  id
  revision
  status
  createdAt
  decidedAt
  pet { id, name, primaryImage }
}

export view AdoptionRequestDetails from AdoptionRequest {
  id
  revision
  status
  motivation
  decisionReason
  createdAt
  decidedAt
  pet { id, revision, name, primaryImage, status }
}
