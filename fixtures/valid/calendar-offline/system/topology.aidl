module calendar.system.topology

import calendar.domain.CalendarEvent
import calendar.sync.CalendarEventSync
import calendar.system.resources.*

export service CalendarService {
  owns [CalendarEvent]
  uses [CalendarDb, CalendarChanges]
  runs [sync CalendarEventSync]
  reliability {
    syncStore CalendarDb
  }
  telemetry inherit
}

export system CalendarSystem {
  services [CalendarService]
  resources [CalendarDb, CalendarChanges, CalendarLocal]
}
