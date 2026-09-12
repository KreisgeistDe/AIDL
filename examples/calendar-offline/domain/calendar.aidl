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
  field id: uuid primary clientGenerated immutable
  field revision: revision generated concurrencyToken
  field ownerId: SubjectId required immutable
  field title: string(1..200) required mutable
  field description: string(0..4000) default "" mutable sensitive
  field startsAt: datetime required mutable
  field endsAt: datetime required mutable
  field attendees: set<email> default [] mutable sensitive
  field visibility: CalendarVisibility default private mutable
  field deletedAt: datetime? generated mutable
  field createdAt: datetime generated immutable
  field updatedAt: datetime generated mutable

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
