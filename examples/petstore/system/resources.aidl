module petstore.system.resources

export resource PetstoreDb sql {
  consistency strong
  transactions [readCommitted, repeatableRead, serializable]
  migrations expandBackfillContract
  backup rpo 15m rto 1h
  encryption required
}

