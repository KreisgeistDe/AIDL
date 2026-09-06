module fixtures.valid.basic

export enum Status { active, archived }

export value Item {
  id: uuid required
  name: string(1..80) required
  status: Status required
}
