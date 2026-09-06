module videohub.system.topology

import videohub.contracts.events.*
import videohub.domain.catalog.*
import videohub.domain.media.*
import videohub.domain.comments.*
import videohub.operations.catalog.*
import videohub.operations.media.*
import videohub.operations.search.*
import videohub.operations.comments.*
import videohub.operations.analytics.*
import videohub.system.resources.*
import videohub.system.api.VideoHubApi

export service CatalogService {
  owns [Channel, Video]
  uses [MetadataDb, MediaEvents, VideoEvents]
  exposes [
    query listPublicVideos,
    query getPlayableVideo,
    query authorizeVideoUpload,
    query authorizeComment,
    mutation createChannel,
    mutation createDraftVideo,
    mutation attachReadyMedia
  ]
  runs [consumer AttachReadyMedia]
  reliability {
    idempotencyStore MetadataDb
    inboxStore MetadataDb
  }
  telemetry inherit
}

export service MediaService {
  owns [MediaAsset]
  uses [
    MediaDb,
    VideoObjects,
    RenditionObjects,
    ManifestObjects,
    VideoDelivery,
    TranscodeJobs,
    MediaEvents
  ]
  dependsOn [CatalogService]
  exposes [
    mutation beginVideoUpload,
    mutation completeVideoUpload,
    query getMediaAsset,
    mutation markMediaReady
  ]
  runs [
    task TranscodeVideo,
    workflow ProcessUploadedVideo,
    consumer StartTranscoding
  ]
  reliability {
    idempotencyStore MediaDb
    inboxStore MediaDb
    workflowStore MediaDb
  }
  telemetry inherit
}

export service SearchService {
  uses [VideoEvents, VideoSearch, SearchState]
  exposes [query searchVideos]
  runs [projection PublicVideoSearch]
  reliability {
    projectionStore SearchState
  }
  telemetry inherit
}

export service CommentsService {
  owns [Comment]
  uses [CommentsDb, CommentEvents]
  dependsOn [CatalogService]
  exposes [
    query listComments,
    mutation addComment,
    channel LiveComments
  ]
  runs [channel LiveComments]
  reliability {
    idempotencyStore CommentsDb
  }
  telemetry inherit
}

export service AnalyticsService {
  uses [WatchEvents, WatchArchive, ViewCounters, AnalyticsState]
  exposes [
    mutation recordWatch,
    query getViewCount
  ]
  runs [
    projection WatchArchiveProjection,
    projection ViewCountProjection
  ]
  reliability {
    idempotencyStore AnalyticsState
    projectionStore AnalyticsState
  }
  telemetry inherit
}

export system VideoHubSystem {
  services [
    CatalogService,
    MediaService,
    SearchService,
    CommentsService,
    AnalyticsService
  ]
  resources [
    MetadataDb,
    MediaDb,
    CommentsDb,
    SearchState,
    AnalyticsState,
    VideoObjects,
    RenditionObjects,
    ManifestObjects,
    VideoDelivery,
    TranscodeJobs,
    MediaEvents,
    VideoEvents,
    CommentEvents,
    VideoSearch,
    ViewCounters,
    WatchEvents,
    WatchArchive
  ]
  apis [VideoHubApi]
  channels [LiveComments]
}
