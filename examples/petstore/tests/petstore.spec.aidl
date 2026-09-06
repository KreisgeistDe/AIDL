module petstore.tests

import petstore.domain.pets.*
import petstore.domain.adoptions.*
import petstore.operations.pets.*
import petstore.operations.adoptions.*
import petstore.ui.pages.*

test "public visitor lists only available pets" target backend {
  arrange {
    availablePet = fixture Pet(status: available)
    adoptedPet = fixture Pet(
      status: adopted,
      adoptedAt: now()
    )
  }
  act result = call listAvailablePets({}, { size: 12 })
  assert result.items contains availablePet
  assert result.items excludes adoptedPet
}

test "request persists applicant data and terms" target fullstack {
  arrange {
    pet = fixture Pet(status: available)
    user = fixture Principal(subjectId: SubjectId("user-1"))
  }
  as user call requestAdoption({
    operationId: operationId(),
    petId: pet.id,
    expectedPetRevision: pet.revision,
    fullName: "Ada Example",
    email: "ada@example.test",
    motivation: "Wir können dem Tier ein dauerhaftes Zuhause bieten.",
    acceptedTerms: true
  })
  assert stored AdoptionRequest where
    applicantId == user.subjectId
    and applicantName == "Ada Example"
    and termsAcceptedAt != null
  assert stored Pet where id == pet.id and status == pending
  assert emitted AdoptionRequested exactly 1 logical
}

test "idempotent retry returns the same adoption" target backend {
  arrange {
    pet = fixture Pet(status: available)
    user = fixture Principal(subjectId: SubjectId("user-1"))
    operationId = operationId()
    input = fixture AdoptionRequestInput(
      operationId: operationId,
      petId: pet.id,
      expectedPetRevision: pet.revision
    )
  }
  as user act first = call requestAdoption(input)
  as user act second = call requestAdoption(input)
  assert first.id == second.id
  assert count AdoptionRequest where pet.id == pet.id equals 1
  assert emitted AdoptionRequested exactly 1 logical
}

test "only one concurrent request reserves a pet" target concurrency {
  arrange {
    pet = fixture Pet(status: available)
    firstUser = fixture Principal(subjectId: SubjectId("user-1"))
    secondUser = fixture Principal(subjectId: SubjectId("user-2"))
  }
  parallel {
    as firstUser a = call requestAdoption(
      fixture AdoptionRequestInput(
        petId: pet.id,
        expectedPetRevision: pet.revision
      )
    )
    as secondUser b = call requestAdoption(
      fixture AdoptionRequestInput(
        petId: pet.id,
        expectedPetRevision: pet.revision
      )
    )
  }
  assert exactlyOne [a, b] is success
  assert exactlyOne [a, b] is error in [ConcurrentChange, PetUnavailable]
  assert count AdoptionRequest where pet.id == pet.id equals 1
  assert stored Pet where id == pet.id and status == pending
}

test "outbox survives crash and duplicate delivery" target failure {
  arrange {
    pet = fixture Pet(status: available)
    user = fixture Principal(subjectId: SubjectId("user-1"))
  }
  crashpoint afterDatabaseCommit beforeTopicPublish
  as user call requestAdoption(
    fixture AdoptionRequestInput(
      petId: pet.id,
      expectedPetRevision: pet.revision
    )
  )
  restart service PetstoreService
  deliver pending
  duplicate lastDelivery times 2
  assert workflow ReviewAdoption started exactly 1 logical
}

test "review timeout releases the pet" target workflow {
  arrange {
    pet = fixture Pet(status: pending)
    request = fixture AdoptionRequest(
      pet: pet,
      status: submitted
    )
  }
  start workflow ReviewAdoption({
    requestId: request.id
  })
  advance clock 10d
  trigger approval timeout
  assert stored AdoptionRequest where
    id == request.id
    and status == expired
    and decidedAt != null
  assert stored Pet where id == pet.id and status == available
}

test "visitor filters available dogs" target ui {
  arrange fixture Pet(name: "Milo", species: dog, status: available)
  visit PetCatalog
  fill PetFilters.species with dog
  assert visible PetCard where heading == "Milo"
  assert url.query.species == "dog"
  assert a11y hasNoViolations
}

test "anonymous user cannot open adoption form" target ui {
  visit AdoptionPage(petId: uuid())
  assert navigated Login
  assert route.returnTo is set
}
