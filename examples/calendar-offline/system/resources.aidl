module calendar.system.resources

import calendar.domain.CalendarEventView

export resource CalendarDb sql {
  consistency strong
  transactions [readCommitted, serializable]
  migrations expandBackfillContract
  backup rpo 15m rto 1h
  encryption required
}

export resource CalendarLocal localStore {
  engine sqlite
  encryption required
  quota 250MB
  schemaMigrations required
  erase on signOut
}

export resource CalendarChanges stream<CalendarEventView> {
  partition by ownerId
  retention 180d
  replay enabled
}

