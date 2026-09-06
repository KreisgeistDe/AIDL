module calendar.system.api

import calendar.operations.listMyEvents
import calendar.sync.CalendarEventSync

export api CalendarApi {
  transport rest
  version 1
  basePath "/api/v1"
  operations [
    query listMyEvents,
    sync CalendarEventSync
  ]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 600 per 1m burst 100
}

