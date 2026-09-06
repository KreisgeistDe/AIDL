module calendar.ui.app

import aidl.ui.std.*
import calendar.ui.pages.*

export theme CalendarTheme {
  color primary "#175CD3"
  color surface "#FFFFFF"
  color text "#101828"
  color warning "#B54708"
  color danger "#B42318"
  spacing scale [4, 8, 12, 16, 24]
  contrast minimum AA
}

export frontend CalendarWeb {
  target web
  rendering client
  theme CalendarTheme
  locale default "de-DE" supported ["de-DE", "en-US"]
  route "/" -> CalendarPage auth authenticated
  fallback -> NotFoundPage
}

