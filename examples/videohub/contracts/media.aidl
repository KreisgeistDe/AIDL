module videohub.contracts.media

export media VideoObject {
  types ["video/mp4", "video/webm", "video/quicktime"]
  maxSize 20GB
  inspect antivirus required
  metadata [duration, width, height, codec]
}

export media StreamingManifest {
  types [
    "application/vnd.apple.mpegurl",
    "application/dash+xml"
  ]
  maxSize 10MB
}

export rendition Hd1080 from VideoObject {
  container "mp4"
  videoCodec "h264"
  maxResolution "1920x1080"
  audioCodec "aac"
}

export rendition Hd720 from VideoObject {
  container "mp4"
  videoCodec "h264"
  maxResolution "1280x720"
  audioCodec "aac"
}
