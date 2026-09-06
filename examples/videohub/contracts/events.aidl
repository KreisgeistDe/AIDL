module videohub.contracts.events

import videohub.contracts.identifiers.*
import videohub.contracts.media.*

export event VideoUploadCompleted version 1 {
  eventId: OperationId required
  assetId: MediaAssetId required
  videoId: VideoId required
  source: BlobHandle<VideoObject> required
  occurredAt: datetime required
}

export event MediaReady version 1 {
  eventId: OperationId required
  assetId: MediaAssetId required
  videoId: VideoId required
  playbackManifest: DeliveryHandle<StreamingManifest> required
  duration: duration required
  occurredAt: datetime required
}

export event VideoPublished version 1 {
  eventId: OperationId required
  videoId: VideoId required
  channelId: ChannelId required
  title: string(1..200) required
  description: string(0..5000) required
  publishedAt: datetime required
  occurredAt: datetime required
}

export event CommentAdded version 1 {
  eventId: OperationId required
  commentId: CommentId required
  videoId: VideoId required
  authorDisplayName: string(1..120) required
  body: string(1..2000) required
  createdAt: datetime required
  occurredAt: datetime required
}

export topic MediaEvents {
  events [VideoUploadCompleted, MediaReady]
  delivery atLeastOnce
  partition by videoId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}

export topic VideoEvents {
  events [VideoPublished]
  delivery atLeastOnce
  partition by videoId
  ordering perPartition
  retention 365d
  compatibility backward
  deadLetter after 12 attempts
}

export topic CommentEvents {
  events [CommentAdded]
  delivery atLeastOnce
  partition by videoId
  ordering perPartition
  retention 7d
  compatibility backward
  deadLetter after 8 attempts
}
