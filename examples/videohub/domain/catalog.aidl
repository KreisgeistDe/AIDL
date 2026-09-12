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
  field id: ChannelId primary generated immutable
  field revision: revision generated concurrencyToken
  field ownerId: SubjectId required immutable
  field name: string(1..120) required mutable
  field description: string(0..2000) default "" mutable
  field createdAt: datetime generated immutable

  index byOwner(ownerId, createdAt desc)
}

export entity Video {
  field id: VideoId primary generated immutable
  field revision: revision generated concurrencyToken
  field channel: ref Channel required immutable onDelete restrict
  field title: string(1..200) required mutable
  field description: string(0..5000) default "" mutable
  field status: VideoStatus default draft mutable
  field visibility: VideoVisibility default private mutable
  field assetId: MediaAssetId? mutable
  field playbackManifest: DeliveryHandle<StreamingManifest>? mutable
  field duration: duration? mutable
  field publishedAt: datetime? mutable
  field createdAt: datetime generated immutable
  field updatedAt: datetime generated mutable

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
