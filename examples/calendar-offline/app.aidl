module calendar

import calendar.system.topology.CalendarSystem
import calendar.system.api.CalendarApi
import calendar.ui.app.CalendarWeb

app OfflineCalendar {
  profile core version 1
  profile web version 1
  profile distributed version 1
  profile offline version 1
  profile cloud version 1
  system CalendarSystem
  frontend CalendarWeb
  api CalendarApi
  defaultDeployment local
}

auth {
  provider oidc config("OIDC_ISSUER")
  subject claim "sub" as SubjectId
  roles [user, admin]
  serviceIdentities required
}

a11y {
  standard WCAG_2_2_AA
  keyboard required
  focus visible
  reducedMotion respect
}

privacy {
  sensitiveFields encrypt
  localData erase on signOut
  deviceRevocation remoteWipeOnNextConnection
}
