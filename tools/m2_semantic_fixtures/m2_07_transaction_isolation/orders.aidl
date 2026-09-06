module example.orders
resource OrderDb sql {
  transactions [readCommitted, serializable]
}
mutation ChangeOrder {
  auth: authenticated
  allow: true
  errors: [InvalidInput]
  idempotency: none
  transaction on OrderDb {
    write: OrderDb.update()
  }
}
service OrdersService {
  uses [OrderDb]
  exposes [mutation ChangeOrder]
}
