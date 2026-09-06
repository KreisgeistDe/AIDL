module videohub.policies

import videohub.contracts.identifiers.*
import videohub.domain.catalog.*

export policy canManageChannel(channelId: ChannelId) -> bool {
  require principal.authenticated
  channel = Channel.byId(channelId)
  return channel != null
      and (
        channel.ownerId == principal.subjectId
        or principal.hasRole(admin)
      )
}

export policy canManageVideo(videoId: VideoId) -> bool {
  require principal.authenticated
  video = Video.byId(videoId)
  return video != null
      and (
        video.channel.ownerId == principal.subjectId
        or principal.hasRole(admin)
      )
}

