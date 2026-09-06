module videohub.tests

import videohub.contracts.analytics.WatchEvent
import videohub.domain.catalog.*
import videohub.domain.media.*
import videohub.operations.catalog.*
import videohub.operations.media.*
import videohub.operations.search.*

test "service ownership has no cross-service refs" target topology {
  assert owner Video equals CatalogService
  assert owner MediaAsset equals MediaService
  assert Video.assetId is nominalId not ref
  assert MediaAsset.videoId is nominalId not ref
  assert no service reads foreignStore
}

test "resumable upload retains operation identity" target media {
  arrange creator = fixture Principal(role: creator)
  as creator begin upload fixture BeginUploadInput()
  upload chunks [1, 2, 3]
  disconnect after chunk 2
  reconnect
  resume same session
  assert uploaded chunks exactly [1, 2, 3]
  assert checksum verified
}

test "duplicate upload events start one logical workflow" target failure {
  arrange event = fixture VideoUploadCompleted()
  deliver event
  duplicate event times 3
  assert workflow ProcessUploadedVideo started exactly 1 logical
  assert task TranscodeVideo completed exactly 1 logical
}

test "media-ready event attaches asset idempotently" target failure {
  arrange {
    video = fixture Video(status: draft, visibility: public)
    event = fixture MediaReady(videoId: video.id)
  }
  deliver event
  duplicate event times 2
  assert stored Video where
    id == video.id
    and status == ready
    and assetId == event.assetId
  assert emitted VideoPublished exactly 1 logical
}

test "search projection rebuild converges" target projection {
  arrange events = fixtures VideoPublished(count: 1000)
  replay events shuffledWithDuplicates
  rebuild projection PublicVideoSearch
  assert projection checkpoint complete
  assert count VideoSearchDocument equals 1000
  assert projection lag <= 30s
}

test "view counter rebuild uses durable archive" target projection {
  arrange records = fixtures WatchEvent(count: 10000)
  project records into WatchArchive
  erase resource ViewCounters
  rebuild projection ViewCountProjection from WatchArchive
  assert total ViewCounters equals 10000
  assert no viewerId exposed
}

test "realtime reconnect resumes or falls back" target realtime {
  connect channel LiveComments(videoId: fixture VideoId())
  receive comments count 5
  disconnect
  publish comments count 3
  reconnect cursor lastSeen
  assert received all comments exactlyOnce logical
  assert physical duplicates deduplicated by eventId
}

test "global deployment preserves minimum availability" target deployment {
  select deployment global
  fail zone "eu-central-a"
  assert CatalogService healthyReplicas >= 2 in remainingRegions
  assert VideoDelivery available
  assert no activeActive writes inferred for MetadataDb
}
