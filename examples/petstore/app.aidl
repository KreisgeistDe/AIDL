module petstore

import petstore.system.topology.PetstoreSystem
import petstore.system.api.PetstoreApi
import petstore.ui.app.PetstoreWeb

app Petstore {
  profile core version 1
  profile web version 1
  profile distributed version 1
  profile cloud version 1
  system PetstoreSystem
  frontend PetstoreWeb
  api PetstoreApi
  defaultDeployment local
}

auth {
  provider oidc config("OIDC_ISSUER")
  subject claim "sub" as SubjectId
  roles [customer, shelterStaff, admin]
  scopes [pets.read, pets.write, adoptions.read, adoptions.write]
  serviceIdentities required
}

a11y {
  standard WCAG_2_2_AA
  keyboard required
  focus visible
  reducedMotion respect
  images requireAlt
}

privacy {
  sensitiveFields redact
  auditRetention 365d
  localData erase on signOut
}
