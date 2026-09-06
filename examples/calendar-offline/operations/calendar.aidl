module calendar.operations

import calendar.domain.*
import calendar.system.resources.CalendarDb

export query listMyEvents(
  filter: CalendarFilter,
  page: PageInput default { size: 100 }
) -> Page<CalendarEventView> {
  auth: authenticated
  allow: principal.authenticated
  read: CalendarEvent.where(
                      ownerId == principal.subjectId
                      and startsAt < filter.until
                      and endsAt > filter.from
                    )
                    .filterDeleted(filter.includeDeleted)
                    .sort(startsAt asc)
                    .page(page)
                    .project(CalendarEventView)
  consistency: session
  errors: [
    NotAuthenticated,
    InvalidInput,
    UpgradeRequired,
    InternalFailure
  ]
  timeout: 3s
}

