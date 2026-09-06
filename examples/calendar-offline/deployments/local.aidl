module calendar.deployments.local

import calendar.system.topology.CalendarSystem
import calendar.system.resources.*

export deployment local for CalendarSystem {
  environment development
  target process
  colocate services all
  bind CalendarDb container "postgres:17"
  bind CalendarChanges memory
}

