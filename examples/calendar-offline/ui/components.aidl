module calendar.ui.components

import aidl.ui.std.*
import calendar.domain.CalendarEventView

export component CalendarEventCard(
  event: CalendarEventView,
  onRename: action
) {
  semantic article label event.title
  heading level 2 text event.title
  text formatDateTimeRange(event.startsAt, event.endsAt)
  badge text event.visibility.label tone neutral
  when event.deletedAt == null {
    button "Umbenennen" action onRename
  }
}

export component SyncSummary(
  status: SyncStatus<CalendarEventView>
) {
  semantic status
  text status.summary
}

export component PendingChangeBadge() {
  badge text "Noch nicht synchronisiert" tone warning
}

export component CalendarConflictResolver() {
  semantic alert
  heading level 2 text "Zeitkonflikt"
  text "Wähle eine der beiden Terminzeiten."
}

export component RejectedChangeNotice() {
  semantic alert
  text "Die lokale Änderung wurde abgelehnt und bleibt zur Prüfung erhalten."
}

