module parity.legacy

export entity Pet {
  id: uuid primary
  revision: revision generated concurrencyToken
}
