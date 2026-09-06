module videohub.operations.comments

import videohub.contracts.events.*
import videohub.contracts.identifiers.*
import videohub.domain.comments.*
import videohub.domain.errors.*
import videohub.operations.catalog.authorizeComment
import videohub.system.resources.CommentsDb

@publicReason("Öffentliche Kommentare eines sichtbaren Videos.")
export query listComments(
  forVideoId: VideoId,
  page: PageInput default { size: 100 }
) -> Page<CommentView> {
  auth: public
  read: Comment.where(
                 videoId == forVideoId
                 and deletedAt == null
               )
               .sort(createdAt asc)
               .page(page)
               .project(CommentView)
  consistency: strong
  cache: public ttl 5s vary [forVideoId, page]
  errors: [InvalidInput, InternalFailure]
  timeout: 2s
}

export mutation addComment(
  input: AddCommentInput
) -> CommentView {
  auth: authenticated
  allow: principal.authenticated
  errors: [
    NotAuthenticated,
    NotAuthorized,
    VideoNotFound,
    InvalidInput,
    InternalFailure
  ]
  authorize: remote query authorizeComment(input.videoId)
    else VideoNotFound
  idempotency: {
    key input.operationId
    scope principal.subjectId
    retain 30d
  }
  transaction on CommentsDb isolation readCommitted {
    comment = Comment.create({
      videoId: input.videoId,
      authorId: principal.subjectId,
      authorDisplayName: principal.displayName,
      body: input.body
    })
    emit: CommentAdded(
      eventId: operationId(),
      commentId: comment.id,
      videoId: comment.videoId,
      authorDisplayName: comment.authorDisplayName,
      body: comment.body,
      createdAt: comment.createdAt,
      occurredAt: now()
    ) to CommentEvents via outbox
    return CommentView(comment)
  }
  audit: required
  timeout: 3s
}

export channel LiveComments {
  transport websocket
  message CommentAdded
  source CommentEvents
  filter by videoId
  delivery atLeastOnce
  ordering perPartition
  resume cursor
  backpressure dropOldest maxBuffered 100
  auth public
  fallback query listComments
}
