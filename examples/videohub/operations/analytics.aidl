module videohub.operations.analytics

import videohub.contracts.analytics.*
import videohub.contracts.identifiers.VideoId
import videohub.system.resources.*

@publicReason("Anonyme oder authentifizierte Wiedergabe-Telemetrie.")
export mutation recordWatch(
  input: RecordWatchInput
) -> bool {
  auth: public
  allow: true
  errors: [InvalidInput, RateLimited, InternalFailure]
  idempotency: {
    key input.eventId
    scope input.sessionId
    retain 7d
  }
  call: WatchEvents.append(WatchEvent(
    eventId: input.eventId,
    videoId: input.videoId,
    viewerId: principal.subjectId,
    sessionId: input.sessionId,
    watched: input.watched,
    occurredAt: now()
  ))
  audit: none
  timeout: 1s
}

export projection ViewCountProjection
  from [WatchEvent]
  into ViewCounters {
  key event.videoId
  map increment(event.videoId, 1)
  checkpoint perPartition
  rebuild from WatchArchive
  maxLag 30s
}

export projection WatchArchiveProjection
  from [WatchEvent]
  into WatchArchive {
  key event.eventId
  map event
  checkpoint perPartition
  rebuild snapshot
  maxLag 5m
}

@publicReason("Öffentlicher aggregierter Aufrufzähler.")
export query getViewCount(
  videoId: VideoId
) -> int {
  auth: public
  read: ViewCounters.get(videoId, default: 0)
  consistency: boundedStaleness(max: 30s)
  cache: public ttl 10s vary [videoId]
  errors: [InternalFailure]
  timeout: 1s
}
