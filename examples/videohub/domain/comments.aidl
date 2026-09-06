module videohub.domain.comments

import videohub.contracts.identifiers.*

export value AddCommentInput {
  operationId: OperationId required
  videoId: VideoId required
  body: string(1..2000) required
}

export entity Comment {
  id: CommentId primary generated immutable
  revision: revision generated concurrencyToken
  videoId: VideoId required immutable
  authorId: SubjectId required immutable sensitive
  authorDisplayName: string(1..120) required immutable
  body: string(1..2000) required mutable
  createdAt: datetime generated immutable
  deletedAt: datetime? mutable

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
