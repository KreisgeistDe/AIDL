module videohub.system.resources

import videohub.domain.catalog.*
import videohub.domain.media.*
import videohub.domain.comments.*
import videohub.contracts.analytics.WatchEvent
import videohub.contracts.events.VideoEvents
import videohub.contracts.identifiers.VideoId
import videohub.contracts.media.*
import videohub.contracts.search.VideoSearchDocument

export resource MetadataDb sql {
  consistency strong
  transactions [readCommitted, serializable]
  migrations expandBackfillContract
  backup rpo 5m rto 30m
  encryption required
}

export resource MediaDb sql {
  consistency strong
  transactions [readCommitted, serializable]
  migrations expandBackfillContract
  backup rpo 15m rto 1h
  encryption required
}

export resource CommentsDb sql {
  consistency strong
  transactions [readCommitted]
  migrations expandBackfillContract
  backup rpo 30m rto 2h
  encryption required
}

export resource SearchState keyValue {
  consistency strong
  encryption required
  backup rpo 15m rto 1h
}

export resource AnalyticsState keyValue {
  consistency strong
  encryption required
  backup rpo 15m rto 1h
}

export resource VideoObjects blob<VideoObject> {
  upload resumable multipart
  maxObjectSize 20GB
  checksum sha256
  versioning enabled
  encryption required
  lifecycle {
    incompleteUploads expire 24h
  }
}

export resource RenditionObjects blob<VideoObject> {
  upload serviceOnly
  checksum sha256
  versioning enabled
  encryption required
}

export resource ManifestObjects blob<StreamingManifest> {
  upload serviceOnly
  checksum sha256
  versioning enabled
  encryption required
}

export resource VideoDelivery cdn {
  origins [RenditionObjects, ManifestObjects]
  access signed
  cache immutableByHash
  purge bySurrogateKey
}

export queue TranscodeJobs {
  messages [TranscodeJob]
  delivery atLeastOnce
  visibilityTimeout 30m
  deadLetter after 5 attempts
}

export resource VideoSearch search<VideoSearchDocument> {
  consistency eventual
  rebuild from VideoEvents
}

export resource ViewCounters counter {
  key VideoId
  consistency eventual
  flushInterval 10s
}

export resource WatchEvents stream<WatchEvent> {
  partition by videoId
  retention 7d
  replay enabled
}

export resource WatchArchive timeSeries {
  schema WatchEvent
  partition by videoId
  retention 730d
  encryption required
  pseudonymize viewerId
  backup rpo 1h rto 4h
}
