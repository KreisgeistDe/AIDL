module petstore.ui.components

import aidl.ui.std.*
import petstore.domain.pets.*

export component PetCard(pet: PetSummary) {
  semantic article label pet.name
  layout stack gap 12
  image source pet.primaryImage.url alt pet.primaryImage.alt ratio 4:3
  heading level 2 text pet.name
  text pet.shortDescription clamp 3
  row gap 8 {
    badge text pet.species.label tone neutral
    badge text pet.status.label tone success
  }
  button "Details ansehen"
    action navigate PetDetailsPage(petId: pet.id)
}

export component PetGridSkeleton(count: int) {
  grid columns responsive { base: 1, sm: 2, lg: 3 } {
    repeat index in range(0, count) key index {
      render SkeletonCard()
    }
  }
}

export component EmptyState(title: string) {
  semantic status
  layout stack align center gap 12
  heading level 2 text title
  text "Passe die Filter an oder versuche es später erneut."
}

export component ErrorState<E: ErrorValue>(
  error: E,
  retry: action?
) {
  semantic alert
  layout stack align center gap 12
  heading level 2 text "Etwas ist schiefgegangen"
  text error.safeMessage
  when retry != null {
    button "Erneut versuchen" action retry
  }
}

export component ConflictMessage() {
  semantic alert
  heading level 2 text "Der Datensatz wurde inzwischen geändert"
  text "Die aktuellen Daten wurden neu geladen. Bitte prüfe sie erneut."
}

export component PetFilters(filter: binding<PetFilter>) {
  form inline label "Tierkatalog filtern" {
    select bind filter.species label "Tierart"
      options Species includeAny
    number bind filter.minimumAgeMonths
      label "Mindestalter in Monaten" min 0
    number bind filter.maximumAgeMonths
      label "Höchstalter in Monaten" min 0
    button "Filter zurücksetzen" action reset filter
  }
}

