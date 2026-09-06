module calendar.sync

import calendar.domain.*
import calendar.system.resources.*

export sync CalendarEventSync for CalendarEvent {
  mode replicated
  authority serverValidated
  scope: entity.ownerId == principal.subjectId
  localStore CalendarLocal
  serverStore CalendarDb
  maxOfflineDuration 90d

  operationLog {
    type CalendarEventChange
    id operationId
    actor principal.subjectId
    device deviceId
    baseRevision baseRevision
    ordering causal
    retain confirmed 7d
  }

  push batch max 100 retry exponential(maxDelay: 5m)
  pull cursor serverRevision page 500 source CalendarChanges
  changes to CalendarChanges via outbox
  delete tombstone retain 180d

  conflict {
    field title merge lww(clock: serverHlc)
    field description merge lww(clock: serverHlc)
    field attendees merge addWinsSet
    field visibility merge serverWins
    group schedule fields [startsAt, endsAt] merge manual
  }

  rejected retainLocal mark rejected
  schemaMigration required
}
