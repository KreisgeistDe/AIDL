module example.orders
entity Order {
}
resource OrderDb sql {
  transactions [serializable]
}
resource AuditDb sql {
  transactions [serializable]
}
mutation ChangeOrder {
  auth: authenticated
  allow: true
  errors: [InvalidInput]
  idempotency: none
  transaction on AuditDb isolation serializable {
    order = Order.require(input.orderId)
  }
}
service OrdersService {
  owns [Order]
  uses [OrderDb]
  exposes [mutation ChangeOrder]
}
