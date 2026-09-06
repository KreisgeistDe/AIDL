module calendar.ui.pages

import aidl.ui.std.*
import calendar.domain.*
import calendar.operations.listMyEvents
import calendar.sync.CalendarEventSync
import calendar.ui.components.*

export action renameEvent(
  event: CalendarEventView,
  title: string
) {
  enqueue CalendarEventSync.change({
    operationId: operationId(),
    entityId: event.id,
    baseRevision: event.revision,
    change: CalendarEventChange.rename(title)
  })
  pending show PendingChangeBadge()
  conflict show CalendarConflictResolver()
  rejected show RejectedChangeNotice()
}

export page CalendarPage {
  auth authenticated onFailure navigate Login(returnTo: route.current)
  urlState filter: CalendarFilter default currentMonth()
  urlState page: PageInput default { size: 100 }

  data events = query listMyEvents(filter, page)
    consistency session
    offline CalendarEventSync
    refresh on [filter, page]

  loading: CalendarSkeleton()
  empty: EmptyCalendar()
  stale: OfflineDataNotice()
  error retry: ErrorState(error: error, retry: data.retry)

  main {
    heading level 1 text "Kalender"
    render SyncSummary(sync: CalendarEventSync.status)
    calendarGrid {
      repeat event in events.items key event.id {
        render CalendarEventCard(
          event: event,
          onRename: renameEvent.bind(event)
        )
      }
    }
  }
}

syncStatus CalendarEventSync {
  offline OfflineBanner()
  syncing SyncIndicator(pending: status.pendingCount)
  blocked SyncBlocked(error: status.error)
  conflict ConflictCenter(items: status.conflicts)
  rejected RejectedChanges(items: status.rejected)
}
