module petstore.deployments.production

import petstore.system.topology.*
import petstore.system.resources.PetstoreDb
import petstore.contracts.adoption-events.AdoptionEvents

export deployment production for PetstoreSystem {
  environment production
  target containers
  region primary "eu-central"
  dataResidency ["EU"]

  service PetstoreService {
    replicas 2..20
    availability zones minimum 2
    autoscale cpu target 65%
    resources cpu 500mCPU..2cores memory 512MB..2GB
    health {
      readiness "/health/ready"
      liveness "/health/live"
    }
    rollout rolling maxUnavailable 0 maxSurge 1
    shutdown grace 30s
  }

  bind PetstoreDb from secret("PETSTORE_DATABASE_URL")
  bind AdoptionEvents managed

  observability {
    telemetry otel
    traces sample 10%
    sensitiveFields redact
  }

  slo apiAvailability 99.9% window 30d
  slo apiLatency p95 < 300ms window 30d
}
