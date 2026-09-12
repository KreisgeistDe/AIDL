module videohub.domain.comments

import videohub.contracts.identifiers.*

export value AddCommentInput {
  operationId: OperationId required
  videoId: VideoId required
  body: string(1..2000) required
}

export entity Comment {
  field id: CommentId primary generated immutable
  field revision: revision generated concurrencyToken
  field videoId: VideoId required immutable
  field authorId: SubjectId required immutable sensitive
  field authorDisplayName: string(1..120) required immutable
  field body: string(1..2000) required mutable
  field createdAt: datetime generated immutable
  field deletedAt: datetime? mutable

  index byVideo(videoId, createdAt asc)
}

export view CommentView from Comment {
  id
  revision
  videoId
  authorDisplayName
  body
  createdAt
  deletedAt
}
