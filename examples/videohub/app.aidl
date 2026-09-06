module videohub

import videohub.system.topology.VideoHubSystem
import videohub.system.api.VideoHubApi
import videohub.ui.app.VideoHubWeb

app VideoHub {
  profile core version 1
  profile web version 1
  profile distributed version 1
  profile cloud version 1
  profile media version 1
  profile realtime version 1
  system VideoHubSystem
  frontend VideoHubWeb
  api VideoHubApi
  defaultDeployment local
}

auth {
  provider oidc config("OIDC_ISSUER")
  subject claim "sub" as SubjectId
  displayName claim "name"
  roles [viewer, creator, moderator, admin]
  scopes [videos.read, videos.write, comments.read, comments.write]
  serviceIdentities required
}

a11y {
  standard WCAG_2_2_AA
  keyboard required
  focus visible
  reducedMotion respect
  captions requiredForPublishedVideo
}

privacy {
  sensitiveFields redact
  analytics consent required
  watchHistory erase supported
}
