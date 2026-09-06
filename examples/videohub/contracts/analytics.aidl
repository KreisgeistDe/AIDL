module videohub.contracts.analytics

import videohub.contracts.identifiers.VideoId

export value RecordWatchInput {
  eventId: OperationId required
  videoId: VideoId required
  sessionId: uuid required
  watched: duration required
}

export value WatchEvent {
  eventId: OperationId required
  videoId: VideoId required
  viewerId: SubjectId? sensitive
  sessionId: uuid required
  watched: duration required
  occurredAt: datetime required
}
