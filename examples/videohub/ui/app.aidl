module videohub.ui.app

import aidl.ui.std.*
import videohub.ui.pages.*

export theme VideoHubTheme {
  color primary "#D92D20"
  color surface "#FFFFFF"
  color text "#101828"
  color muted "#667085"
  color danger "#B42318"
  spacing scale [4, 8, 12, 16, 24, 32]
  radius card 12
  contrast minimum AA
}

export frontend VideoHubWeb {
  target web
  rendering hybrid
  theme VideoHubTheme
  locale default "de-DE" supported ["de-DE", "en-US"]

  route "/" -> VideoHome
  route "/search" -> VideoSearchPage
  route "/videos/:videoId" -> VideoPage
  route "/upload" -> CreateVideoPage auth authenticated
  route "/upload/:videoId" -> UploadVideoPage auth authenticated
  fallback -> NotFoundPage
}

