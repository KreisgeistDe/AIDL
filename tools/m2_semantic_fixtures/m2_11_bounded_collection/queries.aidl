module example.queries
query ListPets() -> Page<Pet> {
  auth: private
  read: Pet.where(active == true)
}
