module petstore.ui.app

import aidl.ui.std.*
import petstore.ui.theme.PetTheme
import petstore.ui.pages.*

export frontend PetstoreWeb {
  target web
  rendering hybrid
  theme PetTheme
  locale default "de-DE" supported ["de-DE", "en-US"]

  route "/" -> PetCatalog
  route "/pets/:petId" -> PetDetailsPage
  route "/pets/:petId/adopt" -> AdoptionPage auth authenticated
  route "/adoptions" -> MyAdoptions auth authenticated
  route "/adoptions/:requestId" -> AdoptionConfirmation auth authenticated
  fallback -> NotFoundPage

  navigation primary {
    item "Tiere" route PetCatalog
    item "Meine Anfragen" route MyAdoptions
      visible when session.authenticated
  }

  seo defaults {
    titleTemplate "%s | Petstore"
    description "Finde Tiere aus lokalen Tierheimen."
  }
}

