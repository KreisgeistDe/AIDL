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
  field id: MediaAssetId primary generated immutable
  field revision: revision generated concurrencyToken
  field videoId: VideoId required immutable unique
  field source: BlobHandle<VideoObject> required immutable
  field status: MediaStatus default uploaded mutable
  field renditions: RenditionSet<VideoObject>? mutable
  field playbackManifest: DeliveryHandle<StreamingManifest>? mutable
  field duration: duration? mutable
  field failureCode: string(1..200)? mutable
  field createdAt: datetime generated immutable
  field updatedAt: datetime generated mutable

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
