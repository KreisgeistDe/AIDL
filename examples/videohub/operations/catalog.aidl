module videohub.operations.catalog

import videohub.contracts.events.*
import videohub.contracts.identifiers.*
import videohub.domain.catalog.*
import videohub.domain.errors.*
import videohub.policies.*
import videohub.system.resources.MetadataDb

@publicReason("Öffentlicher Videokatalog.")
export query listPublicVideos(
  page: PageInput default { size: 24 }
) -> Page<VideoSummary> {
  auth: public
  read: Video.where(
               visibility == public
               and status == ready
             )
             .sort(publishedAt desc)
             .page(page)
             .project(VideoSummary)
  consistency: strong
  cache: public ttl 30s vary [page]
  errors: [InvalidInput, InternalFailure]
  timeout: 2s
}

@publicReason("Öffentliche oder nicht gelistete Videoseite.")
export query getPlayableVideo(videoId: VideoId) -> VideoDetails? {
  auth: public
  read: Video.where(
               id == videoId
               and status == ready
               and visibility in [public, unlisted]
             )
             .first()
             .project(VideoDetails)
  consistency: strong
  cache: public ttl 15s vary [videoId]
  errors: [InternalFailure]
  timeout: 2s
}

export query authorizeVideoUpload(
  videoId: VideoId,
  subjectId: SubjectId
) -> bool {
  auth: service
  allow: principal.serviceId == "MediaService"
  read: Video.exists(
    id == videoId
    and channel.ownerId == subjectId
  )
  consistency: strong
  errors: [NotAuthenticated, NotAuthorized, InternalFailure]
  timeout: 1s
}

export query authorizeComment(
  videoId: VideoId
) -> bool {
  auth: service
  allow: principal.serviceId == "CommentsService"
  read: Video.exists(
    id == videoId
    and status == ready
    and visibility in [public, unlisted]
  )
  consistency: strong
  errors: [NotAuthenticated, NotAuthorized, InternalFailure]
  timeout: 1s
}

export mutation createChannel(
  input: CreateChannelInput
) -> Channel {
  auth: authenticated
  allow: principal.hasRole(creator) or principal.hasRole(admin)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    InvalidInput,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }
  transaction on MetadataDb isolation readCommitted {
    channel = Channel.create({
      ownerId: principal.subjectId,
      name: input.name,
      description: input.description
    })
    return channel
  }
  audit: required
  timeout: 3s
}

export mutation createDraftVideo(
  input: CreateVideoInput
) -> VideoDetails {
  auth: authenticated
  allow: canManageChannel(input.channelId)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    ChannelNotFound,
    InvalidInput,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }
  transaction on MetadataDb isolation readCommitted {
    channel = Channel.require(input.channelId) else ChannelNotFound
    video = Video.create({
      channel: channel,
      title: input.title,
      description: input.description,
      status: draft,
      visibility: input.visibility
    })
    return VideoDetails(video)
  }
  audit: required
  timeout: 3s
}

export mutation attachReadyMedia(
  input: AttachMediaInput
) -> VideoDetails {
  auth: service
  allow: principal.serviceId == "CatalogService"
  errors: [
    NotAuthenticated,
    NotAuthorized,
    VideoNotFound,
    MediaAlreadyAttached,
    ConcurrentChange,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope "media-ready"
    retain 365d
  }
  transaction on MetadataDb isolation serializable {
    video = Video.byId(input.videoId) lock update timeout 1s
    require video != null else VideoNotFound
    require video.assetId == null else MediaAlreadyAttached
    write: video.update(
      assetId: input.assetId,
      playbackManifest: input.playbackManifest,
      duration: input.duration,
      status: ready,
      publishedAt: choose(
        video.visibility == public,
        now(),
        null
      )
    )
      expect revision video.revision
      else ConcurrentChange

    when video.visibility == public {
      emit: VideoPublished(
        eventId: operationId(),
        videoId: video.id,
        channelId: video.channel.id,
        title: video.title,
        description: video.description,
        publishedAt: video.publishedAt,
        occurredAt: now()
      ) to VideoEvents via outbox
    }

    return VideoDetails(video)
  }
  audit: required
  timeout: 3s
}

export consumer AttachReadyMedia
  on MediaReady from MediaEvents {
  idempotency: event.eventId retain 365d
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 12)
  call: mutation attachReadyMedia({
    operationId: event.eventId,
    videoId: event.videoId,
    assetId: event.assetId,
    playbackManifest: event.playbackManifest,
    duration: event.duration
  })
}
