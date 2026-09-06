module example.catalog
query unsafeQuery() -> string {
  call: Billing.charge()
}
