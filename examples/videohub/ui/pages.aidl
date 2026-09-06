module videohub.ui.pages

import aidl.ui.std.*
import videohub.contracts.identifiers.*
import videohub.contracts.media.VideoObject
import videohub.domain.catalog.*
import videohub.domain.media.*
import videohub.operations.catalog.*
import videohub.operations.media.*
import videohub.operations.search.*
import videohub.operations.comments.*
import videohub.operations.analytics.*
import videohub.system.resources.VideoObjects
import videohub.ui.components.*

export page VideoHome {
  urlState page: PageInput default { size: 24 }
  data videos = query listPublicVideos(page)
    consistency strong
    refresh on [page]
    staleAfter 30s

  loading: VideoGridSkeleton()
  empty: EmptyState(title: "Noch keine Videos")
  error retry: ErrorState(error: error, retry: data.retry)
  title "VideoHub"

  main {
    heading level 1 text "Neue Videos"
    grid columns responsive { base: 1, md: 2, lg: 4 } {
      repeat video in videos.items key video.id {
        render VideoCard(video)
      }
    }
  }
}

export page VideoSearchPage {
  urlState text: string default ""
  urlState page: PageInput default { size: 24 }
  data results = query searchVideos(text, page)
    consistency boundedStaleness(max: 30s)
    refresh on [text, page]

  loading: VideoGridSkeleton()
  empty: EmptyState(title: "Keine Treffer")
  stale: SearchIndexLagNotice()
  error retry: ErrorState(error: error, retry: data.retry)
  title "Videosuche"

  main {
    search bind text label "Videos durchsuchen"
    render SearchResults(results.items)
  }
}

export page VideoPage(videoId: VideoId) {
  data video = query getPlayableVideo(videoId)
    consistency strong
    refresh on [videoId]
  data views = query getViewCount(videoId)
    consistency boundedStaleness(max: 30s)
    refresh on [videoId]
  data comments = subscribe LiveComments(videoId)
    resume cursor lastSeen
    reconnect exponential(maxDelay: 30s)
    fallback query listComments(videoId)

  loading: VideoPageSkeleton()
  empty: NotFoundState(title: "Video nicht gefunden")
  stale: ViewCountMayLag()
  error retry: ErrorState(error: error, retry: data.retry)
  title video.title

  main {
    videoPlayer source video.playbackManifest
      captions required controls accessible
    heading level 1 text video.title
    text video.description
    text views + " Aufrufe"
    render LiveCommentList(comments)
  }
}

export form CreateVideoForm for CreateVideoInput {
  state createOperationId: OperationId
    default operationId() retain until settled
  field channelId label "Kanal"
  field title label "Titel"
  field description label "Beschreibung" multiline
  field visibility label "Sichtbarkeit"
  validate on blur and submit
  submit call createDraftVideo({
    operationId: createOperationId,
    ...values
  }) {
    pending disableSubmit show Spinner()
    success navigate UploadVideoPage(videoId: result.id)
    failure show FormError(
      fields: error.fieldErrors,
      message: error.safeMessage
    )
  }
}

export page CreateVideoPage {
  auth authenticated onFailure navigate Login(returnTo: route.current)
  title "Video anlegen"
  main {
    heading level 1 text "Video anlegen"
    render CreateVideoForm()
  }
}

export page UploadVideoPage(videoId: VideoId) {
  auth authenticated onFailure navigate Login(returnTo: route.current)
  state beginOperationId: OperationId default operationId() retain until settled
  state completeOperationId: OperationId default operationId() retain until settled
  title "Video hochladen"

  main {
    heading level 1 text "Video hochladen"
    upload video to VideoObjects {
      mode resumable
      accept ["video/mp4", "video/webm", "video/quicktime"]
      maxSize 20GB
      session call beginVideoUpload({
        operationId: beginOperationId,
        videoId: videoId,
        mediaType: file.mediaType,
        sizeBytes: file.sizeBytes,
        checksumSha256: file.sha256
      })
      progress show UploadProgress()
      paused show ResumeUpload()
      completed call completeVideoUpload({
        operationId: completeOperationId,
        videoId: videoId,
        source: upload.blob
      })
      success navigate VideoPage(videoId: videoId)
      rejected show UploadError(error.safeMessage)
    }
  }
}
