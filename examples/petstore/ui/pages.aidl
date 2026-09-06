module petstore.ui.pages

import aidl.ui.std.*
import petstore.domain.pets.*
import petstore.domain.adoptions.*
import petstore.domain.errors.*
import petstore.operations.pets.*
import petstore.operations.adoptions.*
import petstore.ui.components.*

export page PetCatalog {
  title "Tiere zur Adoption"
  urlState filter: PetFilter default {}
  urlState page: PageInput default { size: 12 }

  data pets = query listAvailablePets(filter, page)
    consistency strong
    refresh on [filter, page]
    staleAfter 30s

  loading: PetGridSkeleton(count: 6)
  empty: EmptyState(title: "Keine Tiere gefunden")
  error retry: ErrorState(error: error, retry: data.retry)

  main {
    heading level 1 text "Finde dein neues Familienmitglied"
    render PetFilters(bind: filter)
    grid columns responsive { base: 1, sm: 2, lg: 3 } {
      repeat pet in pets.items key pet.id {
        render PetCard(pet)
      }
    }
    pagination bind page total pets.items.size
      hasMore pets.hasMore label "Katalogseiten"
  }
}

export page PetDetailsPage(petId: Pet.id) {
  data pet = query getPet(petId)
    consistency strong
    refresh on [petId]
    staleAfter 30s

  loading: PetDetailsSkeleton()
  empty: NotFoundState(title: "Tier nicht gefunden")
  error retry: ErrorState(error: error, retry: data.retry)

  title pet.name
  main {
    image source pet.primaryImage.url
      alt pet.primaryImage.alt ratio 16:9
    heading level 1 text pet.name
    text pet.description
    text "Alter in Monaten: " + pet.ageMonths
    text "Tierheim: " + pet.shelter.name + ", " + pet.shelter.city
    button "Adoption anfragen"
      action navigate AdoptionPage(petId: pet.id)
      enabled when pet.status == available
  }
}

export form AdoptionForm(pet: PetDetails) for AdoptionRequestInput {
  state requestOperationId: OperationId
    default operationId() retain until settled

  field fullName label "Vollständiger Name" autocomplete name
  field email label "E-Mail" autocomplete email
  field motivation
    label "Warum passt dieses Tier zu dir?" multiline
  field acceptedTerms label "Bedingungen akzeptieren"

  validate on blur and submit
  submit call requestAdoption({
    operationId: requestOperationId,
    petId: pet.id,
    expectedPetRevision: pet.revision,
    ...values
  }) {
    pending disableSubmit show Spinner()
    success navigate AdoptionConfirmation(requestId: result.id)
    failure ConcurrentChange refresh pet show ConflictMessage()
    failure PetUnavailable refresh pet show ConflictMessage()
    failure show FormError(
      fields: error.fieldErrors,
      message: error.safeMessage
    )
  }
}

export page AdoptionPage(petId: Pet.id) {
  auth authenticated onFailure navigate Login(returnTo: route.current)

  data pet = query getPet(petId)
    consistency strong
    refresh on [petId]

  loading: PetDetailsSkeleton()
  empty: NotFoundState(title: "Tier nicht gefunden")
  error retry: ErrorState(error: error, retry: data.retry)

  title "Adoption für " + pet.name
  main {
    heading level 1 text "Adoption für " + pet.name
    render AdoptionForm(pet: pet)
  }
}

export page AdoptionConfirmation(requestId: AdoptionRequest.id) {
  auth authenticated onFailure navigate Login(returnTo: route.current)

  data request = query getAdoption(requestId)
    consistency strong
    refresh on [requestId]

  loading: LoadingState()
  empty: NotFoundState(title: "Adoptionsanfrage nicht gefunden")
  error retry: ErrorState(error: error, retry: data.retry)

  title "Anfrage eingegangen"
  main {
    semantic status
    heading level 1 text "Anfrage eingegangen"
    text "Das Tierheim prüft deine Anfrage."
    link "Zu meinen Anfragen" route MyAdoptions
  }
}

export page MyAdoptions {
  auth authenticated onFailure navigate Login(returnTo: route.current)
  urlState page: PageInput default { size: 20 }

  data requests = query listMyAdoptions(session.subjectId, page)
    consistency strong
    refresh on [page]

  loading: AdoptionListSkeleton()
  empty: EmptyState(title: "Noch keine Adoptionsanfragen")
  error retry: ErrorState(error: error, retry: data.retry)

  title "Meine Anfragen"
  main {
    heading level 1 text "Meine Anfragen"
    list {
      repeat request in requests.items key request.id {
        link request.pet.name
          route AdoptionConfirmation(requestId: request.id)
        badge text request.status.label tone neutral
      }
    }
    pagination bind page hasMore requests.hasMore
      label "Anfrageseiten"
  }
}

seo PetDetailsPage {
  title pet.name + " adoptieren"
  description pet.shortDescription
  canonical route PetDetailsPage(petId: pet.id)
}
