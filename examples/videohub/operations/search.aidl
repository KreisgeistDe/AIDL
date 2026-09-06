module videohub.operations.search

import videohub.contracts.events.*
import videohub.contracts.search.*
import videohub.system.resources.VideoSearch

export projection PublicVideoSearch
  from [VideoPublished]
  into VideoSearch {
  key event.videoId
  map VideoSearchDocument(
    videoId: event.videoId,
    channelId: event.channelId,
    title: event.title,
    description: event.description,
    publishedAt: event.publishedAt
  )
  checkpoint perPartition
  rebuild replay
  maxLag 30s
}

@publicReason("Öffentliche Videosuche.")
export query searchVideos(
  text: string(1..200),
  page: PageInput default { size: 24 }
) -> Page<VideoSearchDocument> {
  auth: public
  read: VideoSearch.search(text).page(page)
  consistency: boundedStaleness(max: 30s)
  cache: public ttl 15s vary [text, page]
  errors: [InvalidInput, DependencyUnavailable, InternalFailure]
  timeout: 2s
}

