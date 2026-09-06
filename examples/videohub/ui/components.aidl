module videohub.ui.components

import aidl.ui.std.*
import videohub.contracts.events.CommentAdded
import videohub.contracts.search.VideoSearchDocument
import videohub.domain.catalog.VideoSummary

export component VideoCard(video: VideoSummary) {
  semantic article label video.title
  heading level 2 text video.title
  text video.channel.name
  when video.duration != null {
    text formatDuration(video.duration)
  }
  button "Video ansehen"
    action navigate VideoPage(videoId: video.id)
}

export component SearchResults(
  items: [VideoSearchDocument]
) {
  list {
    repeat item in items key item.videoId {
      link item.title route VideoPage(videoId: item.videoId)
    }
  }
}

export component LiveCommentList(
  comments: [CommentAdded]
) {
  list label "Live-Kommentare" {
    repeat comment in comments key comment.commentId {
      item {
        text comment.body
      }
    }
  }
}

export component ViewCountMayLag() {
  semantic status
  text "Der Aufrufzähler wird gerade aktualisiert."
}

