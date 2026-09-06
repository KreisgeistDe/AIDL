module petstore.domain.errors

export error PetNotFound {
  code "PET_NOT_FOUND"
  httpStatus 404
  retry never
  safeMessage "Das Tier wurde nicht gefunden."
}

export error PetUnavailable {
  code "PET_UNAVAILABLE"
  httpStatus 409
  retry never
  safeMessage "Das Tier ist nicht mehr verfügbar."
}

export error AdoptionNotFound {
  code "ADOPTION_NOT_FOUND"
  httpStatus 404
  retry never
  safeMessage "Die Adoptionsanfrage wurde nicht gefunden."
}

export error InvalidAdoptionState {
  code "INVALID_ADOPTION_STATE"
  httpStatus 409
  retry never
  safeMessage "Die Adoptionsanfrage kann nicht mehr entschieden werden."
}

