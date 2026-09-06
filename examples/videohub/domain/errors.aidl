module videohub.domain.errors

export error ChannelNotFound {
  code "CHANNEL_NOT_FOUND"
  httpStatus 404
  retry never
  safeMessage "Der Kanal wurde nicht gefunden."
}

export error VideoNotFound {
  code "VIDEO_NOT_FOUND"
  httpStatus 404
  retry never
  safeMessage "Das Video wurde nicht gefunden."
}

export error MediaAssetNotFound {
  code "MEDIA_ASSET_NOT_FOUND"
  httpStatus 404
  retry never
  safeMessage "Das Medienobjekt wurde nicht gefunden."
}

export error UnsupportedMedia {
  code "UNSUPPORTED_MEDIA"
  httpStatus 415
  retry never
  safeMessage "Das Medienformat wird nicht unterstützt."
}

export error ProcessingFailed {
  code "PROCESSING_FAILED"
  httpStatus 502
  retry backoff
  safeMessage "Das Video konnte nicht verarbeitet werden."
}

export error VideoNotReady {
  code "VIDEO_NOT_READY"
  httpStatus 409
  retry after 10s
  safeMessage "Das Video ist noch nicht bereit."
}

export error MediaAlreadyExists {
  code "MEDIA_ALREADY_EXISTS"
  httpStatus 409
  retry never
  safeMessage "Für das Video wurde bereits ein Upload abgeschlossen."
}

export error MediaAlreadyAttached {
  code "MEDIA_ALREADY_ATTACHED"
  httpStatus 409
  retry never
  safeMessage "Dem Video ist bereits ein Medienobjekt zugeordnet."
}
