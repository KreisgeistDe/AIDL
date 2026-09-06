module videohub.domain.catalog

import videohub.contracts.identifiers.*
import videohub.contracts.media.StreamingManifest

export enum VideoStatus { draft, processing, ready, failed }
export enum VideoVisibility { private, unlisted, public }

export value CreateChannelInput {
  operationId: OperationId required
  name: string(1..120) required
  description: string(0..2000) default ""
}

export value CreateVideoInput {
  operationId: OperationId required
  channelId: ChannelId required
  title: string(1..200) required
  description: string(0..5000) default ""
  visibility: VideoVisibility default private
}

export value AttachMediaInput {
  operationId: OperationId required
  videoId: VideoId required
  assetId: MediaAssetId required
  playbackManifest: DeliveryHandle<StreamingManifest> required
  duration: duration required
}

export entity Channel {
  id: ChannelId primary generated immutable
  revision: revision generated concurrencyToken
  ownerId: SubjectId required immutable
  name: string(1..120) required mutable
  description: string(0..2000) default "" mutable
  createdAt: datetime generated immutable

  index byOwner(ownerId, createdAt desc)
}

export entity Video {
  id: VideoId primary generated immutable
  revision: revision generated concurrencyToken
  channel: ref Channel required immutable onDelete restrict
  title: string(1..200) required mutable
  description: string(0..5000) default "" mutable
  status: VideoStatus default draft mutable
  visibility: VideoVisibility default private mutable
  assetId: MediaAssetId? mutable
  playbackManifest: DeliveryHandle<StreamingManifest>? mutable
  duration: duration? mutable
  publishedAt: datetime? mutable
  createdAt: datetime generated immutable
  updatedAt: datetime generated mutable

  index byPublicFeed(visibility, status, publishedAt desc)
  invariant readyHasMedia:
    status != ready
    or (
      assetId != null
      and playbackManifest != null
      and duration != null
    )
  invariant publishedIsReady:
    publishedAt == null
    or (status == ready and visibility == public)
}

export view VideoSummary from Video {
  id
  revision
  title
  status
  visibility
  duration
  publishedAt
  channel { id, name }
}

export view VideoDetails from Video {
  id
  revision
  title
  description
  status
  visibility
  playbackManifest
  duration
  publishedAt
  createdAt
  channel { id, name }
}
