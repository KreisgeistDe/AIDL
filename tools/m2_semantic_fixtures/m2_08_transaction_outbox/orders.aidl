module example.orders
resource OrderDb sql {
  transactions [serializable]
}
mutation ChangeOrder {
  auth: authenticated
  allow: true
  errors: [InvalidInput]
  idempotency: none
  transaction on OrderDb isolation serializable {
    emit: OrderChanged() to OrderEvents
  }
}
service OrdersService {
  uses [OrderDb]
  exposes [mutation ChangeOrder]
}
