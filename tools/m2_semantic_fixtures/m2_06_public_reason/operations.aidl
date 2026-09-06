module example.publicapi
query getPublic() -> string {
  auth: public
  read: PublicData.get()
}
