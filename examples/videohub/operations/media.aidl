module videohub.operations.media

import videohub.contracts.events.*
import videohub.contracts.identifiers.*
import videohub.contracts.media.*
import videohub.domain.errors.*
import videohub.domain.media.*
import videohub.operations.catalog.authorizeVideoUpload
import videohub.system.resources.*

export mutation beginVideoUpload(
  input: BeginUploadInput
) -> UploadSession<VideoObject> {
  auth: authenticated
  allow: principal.hasRole(creator) or principal.hasRole(admin)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    InvalidInput,
    UnsupportedMedia,
    RateLimited,
    InternalFailure
  ]
  authorize: remote query authorizeVideoUpload(
    input.videoId,
    principal.subjectId
  )
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 24h
  }
  call: VideoObjects.beginUpload({
    mediaType: input.mediaType,
    sizeBytes: input.sizeBytes,
    checksumSha256: input.checksumSha256
  })
  audit: required
  timeout: 3s
}

export mutation completeVideoUpload(
  input: CompleteUploadInput
) -> MediaAssetView {
  auth: authenticated
  allow: principal.hasRole(creator) or principal.hasRole(admin)
  errors: [
    NotAuthenticated,
    NotAuthorized,
    InvalidInput,
    UnsupportedMedia,
    MediaAlreadyExists,
    InternalFailure
  ]
  authorize: remote query authorizeVideoUpload(
    input.videoId,
    principal.subjectId
  )
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }
  transaction on MediaDb isolation serializable {
    asset = MediaAsset.create({
      videoId: input.videoId,
      source: input.source,
      status: uploaded
    }) else MediaAlreadyExists
    emit: VideoUploadCompleted(
      eventId: operationId(),
      assetId: asset.id,
      videoId: asset.videoId,
      source: asset.source,
      occurredAt: now()
    ) to MediaEvents via outbox
    return MediaAssetView(asset)
  }
  audit: required
  timeout: 5s
}

export query getMediaAsset(
  assetId: MediaAssetId
) -> MediaAssetView? {
  auth: service
  allow: principal.serviceId == "MediaService"
  read: MediaAsset.byId(assetId).project(MediaAssetView)
  consistency: strong
  errors: [NotAuthenticated, InternalFailure]
  timeout: 2s
}

export task TranscodeVideo(
  input: TranscodeJob
) -> TranscodeOutput {
  execution worker
  queue: TranscodeJobs
  retry: exponential(initial: 5s, maxDelay: 10m, attempts: 5)
  idempotency: input.jobId retain 30d
  resources: cpu 8cores, memory 16GB
  call: native media.transcode(input)
  errors: [UnsupportedMedia, ProcessingFailed]
  timeout: 30m
}

export mutation markMediaReady(
  input: MarkMediaReadyInput
) -> MediaAssetView {
  auth: service
  allow: principal.serviceId == MediaService
  errors: [
    NotAuthenticated,
    NotAuthorized,
    MediaAssetNotFound,
    ConcurrentChange,
    InternalFailure
  ]
  idempotency: {
    key input.operationId
    scope "transcode"
    retain 365d
  }
  transaction on MediaDb isolation serializable {
    asset = MediaAsset.byId(input.assetId) lock update timeout 1s
    require asset != null else MediaAssetNotFound
    write: asset.update(
      status: ready,
      renditions: input.renditions,
      playbackManifest: input.playbackManifest,
      duration: input.duration
    )
      expect revision input.expectedRevision
      else ConcurrentChange
    emit: MediaReady(
      eventId: operationId(),
      assetId: asset.id,
      videoId: asset.videoId,
      playbackManifest: asset.playbackManifest,
      duration: asset.duration,
      occurredAt: now()
    ) to MediaEvents via outbox
    return MediaAssetView(asset)
  }
  audit: required
  timeout: 5s
}

export workflow ProcessUploadedVideo(
  input: TranscodeJob
) -> MediaAssetView {
  budget: duration 2h, attempts 8
  idempotency: input.jobId retain 365d

  step load retry exponential(max: 3) {
    asset = query getMediaAsset(input.assetId)
    require asset != null else MediaAssetNotFound
  }

  step transcode retry exponential(max: 5) {
    output = task TranscodeVideo(input)
  }

  step reload retry exponential(max: 3) {
    current = query getMediaAsset(input.assetId)
    require current != null else MediaAssetNotFound
  }

  step persist retry exponential(max: 3) {
    result = mutation markMediaReady({
      operationId: workflow.stepId,
      assetId: input.assetId,
      expectedRevision: current.revision,
      renditions: output.renditions,
      playbackManifest: output.playbackManifest,
      duration: output.duration
    })
  }

  return result
}

export consumer StartTranscoding
  on VideoUploadCompleted from MediaEvents {
  idempotency: event.eventId retain 365d
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)
  start: workflow ProcessUploadedVideo({
    jobId: event.eventId,
    assetId: event.assetId,
    source: event.source
  })
}

export native function media.transcode {
  implementation: adapter("media.transcode.v1")
  input: TranscodeJob
  output: TranscodeOutput
  errors: [UnsupportedMedia, ProcessingFailed]
  effects: [blob.read, blob.write, cpu]
  capabilities: [
    blob:VideoObjects,
    blob:RenditionObjects,
    blob:ManifestObjects,
    media:Hd1080,
    media:Hd720
  ]
  retrySafe: true
  deterministic: false
  budget: cpu 30m, memory 16GB
  timeout: 30m
}
