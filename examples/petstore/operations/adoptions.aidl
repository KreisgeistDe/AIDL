module petstore.operations.adoptions

import petstore.domain.adoptions.*
import petstore.domain.pets.*
import petstore.domain.errors.*
import petstore.contracts.adoption-events.*
import petstore.policies.access.*
import petstore.system.resources.PetstoreDb

export query getAdoption(
  id: AdoptionRequest.id
) -> AdoptionRequestDetails? {
  auth: authenticated
  allow: canReadAdoption(id)
  read: AdoptionRequest.byId(id).project(AdoptionRequestDetails)
  consistency: strong
  errors: [NotAuthenticated, NotAuthorized, InternalFailure]
  timeout: 2s
}

export query listMyAdoptions(
  subjectId: SubjectId,
  page: PageInput default { size: 20 }
) -> Page<AdoptionRequestSummary> {
  auth: authenticated
  allow:
    principal.subjectId == subjectId
    or principal.hasRole(admin)
  read: AdoptionRequest.where(applicantId == subjectId)
                         .sort(createdAt desc)
                         .page(page)
                         .project(AdoptionRequestSummary)
  consistency: strong
  errors: [
    NotAuthenticated,
    NotAuthorized,
    InvalidInput,
    InternalFailure
  ]
  timeout: 2s
}

export mutation requestAdoption(
  input: AdoptionRequestInput
) -> AdoptionRequestDetails {
  auth: authenticated
  allow: principal.authenticated
  errors: [
    NotAuthenticated,
    NotAuthorized,
    PetNotFound,
    PetUnavailable,
    ConcurrentChange,
    InvalidInput,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }

  transaction on PetstoreDb isolation serializable {
    pet = Pet.require(input.petId) else PetNotFound
    require pet.status == available else PetUnavailable

    write: pet.update(status: pending)
      expect revision input.expectedPetRevision
      else ConcurrentChange

    request = AdoptionRequest.create({
      pet: pet,
      applicantId: principal.subjectId,
      applicantName: input.fullName,
      applicantEmail: input.email,
      status: submitted,
      motivation: input.motivation,
      termsAcceptedAt: now()
    })

    emit: AdoptionRequested(
      eventId: operationId(),
      requestId: request.id,
      petId: pet.id,
      occurredAt: now()
    ) to AdoptionEvents via outbox

    return AdoptionRequestDetails(request)
  }

  audit: required
  timeout: 5s
}

export mutation decideAdoption(
  input: AdoptionDecisionInput
) -> AdoptionRequestDetails {
  auth: authenticated
  allow: canDecideAdoption(input.requestId)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    AdoptionNotFound,
    InvalidAdoptionState,
    ConcurrentChange,
    InvalidInput,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }

  transaction on PetstoreDb isolation serializable {
    request = AdoptionRequest.byId(input.requestId)
      lock update timeout 1s
    require request != null else AdoptionNotFound
    require request.revision == input.expectedRevision
      else ConcurrentChange
    require request.status in [submitted, reviewing]
      else InvalidAdoptionState

    pet = Pet.require(request.pet.id) lock update timeout 1s

    when input.decision == approved {
      write: request.update(
        status: approved,
        decisionReason: input.reason,
        decidedAt: now()
      )
        expect revision input.expectedRevision
        else ConcurrentChange
      write: pet.update(status: adopted, adoptedAt: now())
        expect revision pet.revision
        else ConcurrentChange
    } else {
      write: request.update(
        status: rejected,
        decisionReason: input.reason,
        decidedAt: now()
      )
        expect revision input.expectedRevision
        else ConcurrentChange
      write: pet.update(status: available, adoptedAt: null)
        expect revision pet.revision
        else ConcurrentChange
    }

    return AdoptionRequestDetails(request)
  }

  audit: required
  timeout: 5s
}

export mutation expireAdoption(
  input: ExpireAdoptionInput
) -> AdoptionRequestDetails {
  auth: service
  allow: principal.serviceId == "PetstoreService"
  errors: [
    NotAuthenticated,
    NotAuthorized,
    AdoptionNotFound,
    ConcurrentChange,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope "review-timeout"
    retain 30d
  }

  transaction on PetstoreDb isolation serializable {
    request = AdoptionRequest.byId(input.requestId)
      lock update timeout 1s
    require request != null else AdoptionNotFound

    when request.status in [submitted, reviewing] {
      pet = Pet.require(request.pet.id) lock update timeout 1s
      write: request.update(
        status: expired,
        decisionReason: "Review timeout",
        decidedAt: now()
      )
        expect revision request.revision
        else ConcurrentChange
      write: pet.update(status: available, adoptedAt: null)
        expect revision pet.revision
        else ConcurrentChange
    }

    return AdoptionRequestDetails(request)
  }

  audit: required
  timeout: 5s
}

export workflow ReviewAdoption(
  input: ReviewInput
) -> AdoptionRequestDetails {
  budget: duration 14d, attempts 8
  idempotency: input.requestId retain 30d

  step load retry none {
    initial = query getAdoption(input.requestId)
    require initial != null else AdoptionNotFound
  }

  approval shelterStaff {
    timeout: 10d
    onTimeout: mutation expireAdoption({
      operationId: workflow.stepId,
      requestId: input.requestId
    })
  }

  step reload retry exponential(max: 3) {
    current = query getAdoption(input.requestId)
    require current != null else AdoptionNotFound
  }

  step complete retry exponential(max: 3) {
    result = mutation decideAdoption({
      operationId: workflow.stepId,
      requestId: input.requestId,
      expectedRevision: current.revision,
      decision: approval.decision,
      reason: approval.reason
    })
  }

  return result
}

export consumer StartAdoptionReview
  on AdoptionRequested from AdoptionEvents {
  idempotency: event.eventId retain 30d
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)
  start: workflow ReviewAdoption({
    requestId: event.requestId
  })
}
