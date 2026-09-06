module example.orders
import example.customers.Customer
export entity Order {
  customer: ref Customer required
}
