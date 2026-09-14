module parity.ir.domain

export enum Status { active, archived }

export value PetInput {
  name: string required
  status: Status required
}

export entity Pet {
  id: uuid primary
  name: string required mutable
  status: Status required
  tags: [string]
}
