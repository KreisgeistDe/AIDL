module videohub.domain.media

import videohub.contracts.identifiers.*
import videohub.contracts.media.*

export enum MediaStatus { uploaded, processing, ready, failed }

export value BeginUploadInput {
  operationId: OperationId required
  videoId: VideoId required
  mediaType: string(1..120) required
  sizeBytes: int(min: 1, max: 20000000000) required
  checksumSha256: string(64..64) required
}

export value CompleteUploadInput {
  operationId: OperationId required
  videoId: VideoId required
  source: BlobHandle<VideoObject> required
}

export value MarkMediaReadyInput {
  operationId: OperationId required
  assetId: MediaAssetId required
  expectedRevision: revision required
  renditions: RenditionSet<VideoObject> required
  playbackManifest: DeliveryHandle<StreamingManifest> required
  duration: duration required
}

export value TranscodeJob {
  jobId: OperationId required
  assetId: MediaAssetId required
  source: BlobHandle<VideoObject> required
}

export value TranscodeOutput {
  renditions: RenditionSet<VideoObject> required
  playbackManifest: DeliveryHandle<StreamingManifest> required
  duration: duration required
}

export entity MediaAsset {
  id: MediaAssetId primary generated immutable
  revision: revision generated concurrencyToken
  videoId: VideoId required immutable unique
  source: BlobHandle<VideoObject> required immutable
  status: MediaStatus default uploaded mutable
  renditions: RenditionSet<VideoObject>? mutable
  playbackManifest: DeliveryHandle<StreamingManifest>? mutable
  duration: duration? mutable
  failureCode: string(1..200)? mutable
  createdAt: datetime generated immutable
  updatedAt: datetime generated mutable

  index byVideo(videoId, createdAt desc)
  invariant readyComplete:
    status != ready
    or (
      renditions != null
      and playbackManifest != null
      and duration != null
    )
}

export view MediaAssetView from MediaAsset {
  id
  revision
  videoId
  status
  renditions
  playbackManifest
  duration
  failureCode
}
