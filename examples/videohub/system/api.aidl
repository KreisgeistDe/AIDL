module videohub.system.api

import videohub.operations.catalog.*
import videohub.operations.media.*
import videohub.operations.search.*
import videohub.operations.comments.*
import videohub.operations.analytics.*

export api VideoHubApi {
  transport rest
  version 1
  basePath "/api/v1"
  operations [
    query listPublicVideos,
    query getPlayableVideo,
    mutation createChannel,
    mutation createDraftVideo,
    mutation beginVideoUpload,
    mutation completeVideoUpload,
    query searchVideos,
    query listComments,
    mutation addComment,
    mutation recordWatch,
    query getViewCount,
    channel LiveComments
  ]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principalOrIp 1200 per 1m burst 200
}

