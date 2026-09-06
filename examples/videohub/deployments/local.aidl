module videohub.deployments.local

import videohub.system.topology.VideoHubSystem
import videohub.system.resources.*
import videohub.contracts.events.*

export deployment local for VideoHubSystem {
  environment development
  target process
  colocate services all

  bind MetadataDb container "postgres:17"
  bind MediaDb container "postgres:17"
  bind CommentsDb container "postgres:17"
  bind SearchState memory
  bind AnalyticsState memory
  bind VideoObjects filesystem "./.local/video-objects"
  bind RenditionObjects filesystem "./.local/renditions"
  bind ManifestObjects filesystem "./.local/manifests"
  bind VideoDelivery localProxy
  bind TranscodeJobs memory
  bind MediaEvents memory
  bind VideoEvents memory
  bind CommentEvents memory
  bind VideoSearch localIndex
  bind ViewCounters memory
  bind WatchEvents memory
  bind WatchArchive container "timeseries-local"
}
