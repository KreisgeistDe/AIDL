module parity.canonical
import parity.shared.Types

export enum Status { active, archived }
export value PetInput {
  name: string required
}
export entity Pet {
  field id: uuid primary
  field name: string required mutable
}
