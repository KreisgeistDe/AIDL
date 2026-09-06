module calendar.system.topology

import calendar.domain.CalendarEvent
import calendar.operations.listMyEvents
import calendar.sync.CalendarEventSync
import calendar.system.resources.*
import calendar.system.api.CalendarApi

export service CalendarService {
  owns [CalendarEvent]
  uses [CalendarDb, CalendarChanges]
  exposes [
    query listMyEvents,
    sync CalendarEventSync
  ]
  runs [sync CalendarEventSync]
  reliability {
    idempotencyStore CalendarDb
    syncStore CalendarDb
  }
  telemetry inherit
}

export system CalendarSystem {
  services [CalendarService]
  resources [CalendarDb, CalendarChanges, CalendarLocal]
  apis [CalendarApi]
}
