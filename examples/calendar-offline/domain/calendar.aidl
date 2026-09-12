module calendar.domain

export enum CalendarVisibility { private, shared }

export value NewCalendarEvent {
  id: uuid required
  title: string(1..200) required
  description: string(0..4000) default ""
  startsAt: datetime required
  endsAt: datetime required
  attendees: set<email> default []
  visibility: CalendarVisibility default private

  invariant validRange: endsAt > startsAt
}

export union CalendarEventChange {
  create(event: NewCalendarEvent)
  rename(title: string(1..200))
  describe(description: string(0..4000))
  reschedule(startsAt: datetime, endsAt: datetime)
  addAttendee(attendee: email)
  removeAttendee(attendee: email)
  setVisibility(visibility: CalendarVisibility)
  delete
}

export entity CalendarEvent {
  id: uuid primary clientGenerated immutable
  revision: revision generated concurrencyToken
  ownerId: SubjectId required immutable
  title: string(1..200) required mutable
  description: string(0..4000) default "" mutable sensitive
  startsAt: datetime required mutable
  endsAt: datetime required mutable
  attendees: set<email> default [] mutable sensitive
  visibility: CalendarVisibility default private mutable
  deletedAt: datetime? generated mutable
  createdAt: datetime generated immutable
  updatedAt: datetime generated mutable

  index byOwner(ownerId, startsAt)
  invariant validRange: endsAt > startsAt
}

export view CalendarEventView from CalendarEvent {
  id
  revision
  ownerId
  title
  description
  startsAt
  endsAt
  attendees
  visibility
  deletedAt
  updatedAt
}

export value CalendarFilter {
  from: datetime required
  until: datetime required
  includeDeleted: bool default false

  invariant validRange: until > from
}
