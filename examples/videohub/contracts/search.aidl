module videohub.contracts.search

import videohub.contracts.identifiers.*

export value VideoSearchDocument {
  videoId: VideoId required
  channelId: ChannelId required
  title: string(1..200) required
  description: string(0..5000) required
  publishedAt: datetime required
}

