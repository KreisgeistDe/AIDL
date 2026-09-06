# 3. Frontend-DSL

## Ziel und Grenze

Die Frontend-Schicht beschreibt UI-Semantik, Datenfluss, lokale Persistenz und
Qualitätsanforderungen. Sie ist keine zweite JSX-/CSS-Sprache. Generatoren
dürfen Web-, Mobile- oder Desktop-Technologien wählen, solange der Vertrag
eingehalten wird.

## Frontend, Plattform und Routen

~~~dsl
frontend PetstoreWeb {
  target web
  rendering hybrid
  theme PetTheme
  locale default "de-DE" supported ["de-DE", "en-US"]

  route "/" -> PetCatalog
  route "/pets/:petId" -> PetDetails
  route "/pets/:petId/adopt" -> AdoptionPage auth authenticated
  fallback -> NotFoundPage
}
~~~

Targets sind web, mobile und desktop. Plattformabhängige Fähigkeiten werden als
Capability angefordert; eine Seite darf ihr Vorhandensein nie voraussetzen,
ohne Fallback zu deklarieren.

## Design-Tokens

~~~dsl
theme PetTheme {
  color primary "#2563EB"
  color surface "#FFFFFF"
  color text "#17202A"
  color danger "#B42318"
  spacing scale [4, 8, 12, 16, 24, 32]
  radius card 12
  typography body system(16, 1.5)
  typography heading system(28, 1.2, weight: 700)
  contrast minimum AA
}
~~~

Komponenten dürfen nur deklarierte Tokens verwenden. Freie Designwerte
benötigen visualOverride mit Grund. Generatoren müssen Kontrast- und
Skalierungsregeln nach Zielplattform prüfen.

## Komponenten und generische Komponenten

~~~dsl
component PetCard(pet: PetSummary) {
  semantic article label pet.name
  layout stack gap 12
  image source pet.primaryImage alt pet.imageAlt ratio 4:3
  heading level 2 text pet.name
  button "Details ansehen" action navigate PetDetails(petId: pet.id)
}

component ResultList<T: entityView>(
  items: [T],
  renderItem: component<T>
) {
  list {
    repeat item in items key identity(item)
      render renderItem(item)
  }
}
~~~

Komponenten sind rein. Sie schreiben nicht direkt in Persistenz, Topics oder
freie Netzwerkendpunkte. Generische Komponenten werden pro konkreter
Instanziierung typgeprüft.

## Seiten, Daten und Konsistenz

~~~dsl
page PetCatalog {
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
    render PetFilters(bind: filter)
    grid columns responsive { base: 1, sm: 2, lg: 3 }
      repeat pet in pets.items key pet.id render PetCard(pet)
  }
}
~~~

Für jede asynchrone Quelle sind loading, empty und error verpflichtend, sofern
der Compiler keinen Zustand ausschließen kann. Bei eventual consistency muss
die UI zusätzlich stale- oder refreshing-Verhalten deklarieren.

## State-Modell

| State | Lebensdauer | Persistenz |
|---|---|---|
| urlState | Route/Browser-Historie | URL |
| data | Query-Cache | flüchtig oder profilabhängig |
| form | bis Submit/Reset | flüchtig |
| state | Komponenteninstanz | flüchtig |
| sessionState | authentifizierte Sitzung | sicherer Session Store |
| localState | App-Installation | deklarierter lokaler Store |
| replicatedState | bis Serverbestätigung und darüber hinaus | Sync Engine |

Globaler untypisierter State ist nicht erlaubt. Sensitive Daten dürfen nur in
Stores persistiert werden, deren Verschlüsselungs- und Löschvertrag dies
erlaubt.

## Formulare und Mutationen

~~~dsl
form AdoptionForm(pet: PetSummary) for AdoptionRequestInput {
  state requestOperationId: OperationId
    default operationId() retain until settled

  field fullName label "Vollständiger Name" autocomplete name
  field email label "E-Mail" autocomplete email
  field motivation label "Warum passt dieses Tier zu dir?" multiline
  field acceptedTerms label "Bedingungen akzeptieren"

  validate on blur and submit
  submit call requestAdoption({
    operationId: requestOperationId,
    petId: pet.id,
    expectedPetRevision: pet.revision,
    ...values
  }) {
    pending disableSubmit show Spinner
    success navigate AdoptionConfirmation(requestId: result.id)
    failure ConcurrentChange refresh pet show ConflictMessage
    failure show FormError(error.fieldErrors, error.safeMessage)
  }
}
~~~

Idempotenz-IDs müssen über Netzwerk-Retries stabil bleiben. Der Generator darf
uuid() nicht bei jedem Retry neu auswerten.

## Optimismus und Offline-Aktionen

Ein connected optimistic action setzt einen unmittelbar erreichbaren Server
voraus:

~~~dsl
action favoritePet(petId: Pet.id) {
  call setFavorite(petId)
  optimistic update favorites add petId
  rollback on failure
}
~~~

Eine Offline-Aktion schreibt dagegen in das Operation-Log und wird nicht bei
Netzwerkausfall zurückgerollt:

~~~dsl
action editCalendarTitle(eventId: CalendarEvent.id, title: string) {
  enqueue CalendarEventSync.update(
    operationId: operationId(),
    entityId: eventId,
    patch: { title }
  )
  pending show LocalPendingBadge
  conflict show CalendarConflictResolver
  rejected show RejectedChangeNotice
}
~~~

Destruktive Aktionen benötigen Bestätigung oder Undo. Ein Offline-Delete muss
die Tombstone-Semantik des Sync-Vertrags anzeigen können.

## Sync-Status

Offlinefähige Frontends deklarieren globale und entitätsbezogene Zustände:

~~~dsl
syncStatus CalendarEventSync {
  offline: OfflineBanner()
  syncing: SyncIndicator(pending: status.pendingCount)
  blocked: SyncBlocked(error: status.error)
  conflict: ConflictCenter(items: status.conflicts)
}
~~~

Die UI MUSS rejected und manualConflict behandeln, wenn der Sync-Vertrag diese
Ergebnisse erzeugen kann.

## Realtime-Daten

~~~dsl
data comments = subscribe LiveComments(videoId)
  resume cursor lastSeen
  reconnect exponential(maxDelay: 30s)
  fallback query listComments(videoId)
~~~

Realtime-Quellen benötigen reconnect, resume oder einen vollständigen
Reload-Fallback. UI-Code darf Delivery oder Reihenfolge nicht stärker annehmen
als der Channel-Vertrag.

Eine Query kann einen Offline-Sync-Vertrag als lokale Quelle deklarieren:

~~~dsl
data events = query listMyEvents(filter, page)
  consistency session
  offline CalendarEventSync
  refresh on [filter, page]
~~~

Der Generator liest zuerst den bestätigten lokalen Stand, projiziert ausstehende
Operationen darüber und synchronisiert anschließend. pending, conflict und
rejected bleiben getrennte Zustände.

## Medien-Uploads

~~~dsl
upload video to VideoObjects {
  mode resumable
  accept ["video/mp4", "video/webm"]
  maxSize 20GB
  progress show UploadProgress
  paused show ResumeUpload
  completed call completeVideoUpload(session.id)
  rejected show UploadError(error.safeMessage)
}
~~~

Lokale Dateipfade oder Bytes dürfen nicht in Logs, Telemetrie oder Query-Cache
gelangen. Upload-Tokens sind kurzlebige sensitive Handles.

## Accessibility, SEO und Datenschutz

~~~dsl
a11y {
  standard WCAG_2_2_AA
  keyboard required
  focus visible
  reducedMotion respect
  images requireAlt
}

seo PetDetails {
  title pet.name + " adoptieren"
  description pet.shortDescription
  canonical route PetDetails(petId: pet.id)
}

privacy {
  analytics consent required
  sensitiveFields redact
  localData erase on signOut
}
~~~

Compiler melden fehlende Labels, Heading-Fehler, Fokusverlust, unzureichenden
Kontrast, unbestätigte destruktive Aktionen und unsichere lokale Persistenz als
strukturierte Diagnosen.

## Frontend-Native Escape Hatch

~~~dsl
native component ShelterMap {
  implementation: "./native/shelter-map.tsx#ShelterMap"
  props: ShelterMapProps
  events: [markerSelected(Shelter.id)]
  capabilities: [browser:geolocation, http:maps]
  offline: fallback MapPlaceholder
  ssr: fallback MapPlaceholder
  a11y: audited "2026-08-15"
}
~~~

Native Komponenten müssen Props, Events, Capabilities, Offline-/SSR-Verhalten
und Accessibility-Status offenlegen.
