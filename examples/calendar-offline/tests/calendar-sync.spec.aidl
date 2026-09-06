module calendar.tests

import calendar.domain.*
import calendar.sync.CalendarEventSync

test "offline-created event receives canonical revision" target sync {
  clients [phone]
  disconnect phone
  on phone enqueue CalendarEventSync.change(
    fixture CalendarEventChange.create()
  )
  assert on phone pendingOperations equals 1
  connect phone
  sync phone
  assert on phone pendingOperations equals 0
  assert stored CalendarEvent where revision != null
  assert converged CalendarEvent
}

test "independent concurrent edits merge" target sync {
  arrange event = fixture CalendarEvent(
    title: "Planung",
    attendees: []
  )
  clients [phone, laptop]
  disconnect [phone, laptop]
  on phone edit event.title to "Private Planung"
  on laptop edit event.attendees add "a@example.test"
  connect [phone, laptop]
  sync all
  assert converged CalendarEvent
  assert event.title == "Private Planung"
  assert event.attendees contains "a@example.test"
}

test "schedule fields conflict as an atomic group" target sync {
  arrange event = fixture CalendarEvent()
  clients [phone, laptop]
  disconnect [phone, laptop]
  on phone reschedule event from "2026-09-03T10:00:00Z"
    until "2026-09-03T11:00:00Z"
  on laptop reschedule event from "2026-09-03T14:00:00Z"
    until "2026-09-03T15:00:00Z"
  connect [phone, laptop]
  sync all
  assert conflict group schedule requires manual
  assert invariant CalendarEvent.validRange holds
}

test "tombstone prevents resurrection by an old client" target sync {
  arrange event = fixture CalendarEvent()
  clients [oldPhone, laptop]
  disconnect oldPhone
  on laptop delete event
  sync laptop
  advance clock 30d
  on oldPhone edit event.title to "Veralteter Titel"
  connect oldPhone
  sync oldPhone
  assert event remains deleted
  assert oldPhone operation is rejected
}

test "revoked access rejects queued operations" target sync {
  arrange event = fixture CalendarEvent()
  clients [phone]
  disconnect phone
  on phone edit event.title to "Lokal"
  revoke access phone.principal
  connect phone
  sync phone
  assert operation is rejected NotAuthorized
  assert local change retained marked rejected
}

