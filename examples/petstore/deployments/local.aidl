module petstore.deployments.local

import petstore.system.topology.PetstoreSystem
import petstore.system.resources.PetstoreDb
import petstore.contracts.adoption-events.AdoptionEvents

export deployment local for PetstoreSystem {
  environment development
  target process
  colocate services all
  bind PetstoreDb container "postgres:17"
  bind AdoptionEvents memory
  observability {
    telemetry otel
    traces sample 100%
    sensitiveFields redact
  }
}

