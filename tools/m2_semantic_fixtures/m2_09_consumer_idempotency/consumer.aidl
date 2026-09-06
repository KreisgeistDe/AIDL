module example.orders
consumer ApplyOrder {
  call: refreshOrder(event.id)
}
