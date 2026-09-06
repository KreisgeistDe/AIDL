module videohub.deployments.global

import videohub.system.topology.*
import videohub.system.resources.*
import videohub.contracts.events.*

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
    rollout rolling maxUnavailable 0 maxSurge 10%
    shutdown grace 30s
  }

  service MediaService {
    replicas 3..100
    worker TranscodeVideo {
      replicas 0..500
      autoscale queueDepth target 20
      resources cpu 8cores memory 16GB gpu optional
    }
    rollout rolling maxUnavailable 1 maxSurge 10%
    shutdown grace 60s
  }

  service SearchService {
    replicas 6..100
    placement perRegion minimum 2
    autoscale cpu target 60%
  }

  service CommentsService {
    replicas 6..300
    placement perRegion minimum 2
    autoscale connections target 5000
  }

  service AnalyticsService {
    replicas 3..100
    autoscale streamLag target 30s
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

  resource CommentsDb {
    sharding by videoId
    placement regional
    failover rpo 30m rto 2h promote automatic
  }

  bind MetadataDb from secret("VIDEO_METADATA_DATABASE_URL")
  bind MediaDb from secret("VIDEO_MEDIA_DATABASE_URL")
  bind CommentsDb from secret("VIDEO_COMMENTS_DATABASE_URL")
  bind SearchState managed regional
  bind AnalyticsState managed regional
  bind VideoObjects managed multiRegion
  bind RenditionObjects managed multiRegion
  bind ManifestObjects managed multiRegion
  bind VideoDelivery managed global
  bind TranscodeJobs managed
  bind MediaEvents managed
  bind VideoEvents managed
  bind CommentEvents managed
  bind VideoSearch managed perRegion
  bind ViewCounters managed
  bind WatchEvents managed
  bind WatchArchive managed regional

  observability {
    telemetry otel
    traces sample 1%
    errors sample 100%
    sensitiveFields redact
  }

  slo playbackAvailability 99.99% window 30d
  slo catalogLatency p95 < 250ms window 30d
  slo commentDelivery p95 < 2s window 30d
  slo searchLag p95 < 30s window 30d
}
