module videohub.golden

export opaque ChannelId = uuid
export opaque VideoId = uuid
export opaque MediaAssetId = uuid

export media VideoObject {
  types ["video/mp4", "video/webm", "video/quicktime"]
  maxSize 20GB
  inspect antivirus required
  metadata [duration, width, height, codec]
}

export rendition Hd720 from VideoObject {
  container "mp4"
  videoCodec "h264"
  maxResolution "1280x720"
  audioCodec "aac"
}

export entity Video {
  id: VideoId primary generated immutable
  channelId: ChannelId required immutable
  title: string(1..200) required mutable
  createdAt: datetime generated immutable
}

export entity MediaAsset {
  id: MediaAssetId primary generated immutable
  videoId: VideoId required immutable unique
  createdAt: datetime generated immutable
}

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

export resource VideoDelivery cdn {
  origins [RenditionObjects]
  access signed
  cache immutableByHash
  purge bySurrogateKey
}

export service CatalogService {
  owns [Video]
  uses [MetadataDb]
  telemetry inherit
}

export service MediaService {
  owns [MediaAsset]
  uses [MediaDb, VideoObjects, RenditionObjects, VideoDelivery]
  dependsOn [CatalogService]
  telemetry inherit
}

export system VideoHubSystem {
  services [CatalogService, MediaService]
  resources [MetadataDb, MediaDb, VideoObjects, RenditionObjects, VideoDelivery]
}

export deployment local for VideoHubSystem {
  environment development
  target process
  colocate services all

  bind MetadataDb container "postgres:17"
  bind MediaDb container "postgres:17"
  bind VideoObjects filesystem "./.local/video-objects"
  bind RenditionObjects filesystem "./.local/renditions"
  bind VideoDelivery localProxy
}

export deployment global for VideoHubSystem {
  environment production
  target containers
  regions ["eu-central", "us-east", "ap-southeast"]
  routing latencyAware
  dataResidency ["EU", "US", "APAC"]

  service CatalogService {
    replicas 6..200
    placement perRegion minimum 2
    autoscale cpu target 60%
  }

  service MediaService {
    replicas 3..100
    rollout rolling maxUnavailable 1 maxSurge 10%
    shutdown grace 60s
  }

  resource MetadataDb {
    primary "eu-central"
    replicas readOnly perRegion
    failover rpo 5m rto 30m promote manual
  }

  resource MediaDb {
    primary "eu-central"
    replicas readOnly perRegion
    failover rpo 15m rto 1h promote manual
  }

  bind MetadataDb from secret("VIDEO_METADATA_DATABASE_URL")
  bind MediaDb from secret("VIDEO_MEDIA_DATABASE_URL")
  bind VideoObjects managed multiRegion
  bind RenditionObjects managed multiRegion
  bind VideoDelivery managed global

  observability {
    telemetry otel
    traces sample 1%
    errors sample 100%
    sensitiveFields redact
  }

  slo playbackAvailability 99.99% window 30d
}
