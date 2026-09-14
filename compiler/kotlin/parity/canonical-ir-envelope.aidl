module parity.ir.app
import parity.ir.domain.*

app ParityApp {
  profile core version 1
  system ParitySystem
  defaultDeployment local
}

auth {
  provider oidc
  subject claim "sub"
  roles [user]
  scopes [parity.read]
  serviceIdentities required
}

export service ParityService {
  owns [parity.ir.domain.Pet]
  uses []
  exposes []
  runs []
}

export system ParitySystem {
  services [ParityService]
  resources []
  apis []
}

export deployment local for ParitySystem {
  environment test
  target process
  colocate services all
}
