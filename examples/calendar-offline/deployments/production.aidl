module calendar.deployments.production

import calendar.system.topology.*
import calendar.system.resources.*

export deployment production for CalendarSystem {
  environment production
  target containers
  region primary "eu-central"
  dataResidency ["EU"]

  service CalendarService {
    replicas 3..30
    availability zones minimum 3
    autoscale cpu target 60%
    rollout rolling maxUnavailable 0 maxSurge 1
    shutdown grace 30s
  }

  bind CalendarDb from secret("CALENDAR_DATABASE_URL")
  bind CalendarChanges managed

  slo syncAvailability 99.95% window 30d
  slo syncLatency p95 < 2s window 30d
}

