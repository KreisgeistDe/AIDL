module aidl.core.self

declaration declaration(name: any = name(required), args: any = args(any, cardinal(0, many))) -> any {
  body body: body(any, name(required), cardinal(0, many))
  body semantic: body(any, name(required), cardinal(0, many))
}

declaration type(name: any = name(required), args: any = args(any, cardinal(0, many))) -> any {
  body body: body(any, name(required), cardinal(0, many))
  body semantic: body(any, name(required), cardinal(0, many))
  semantic alias: "declaration"
}

declaration enum(name: any = name(required)) {
  body case: body(identifier, name(required), cardinal(1, many))
}

declaration entity(name: any = name(required)) {
  body field: body(type, name(required), cardinal(0, many), modifier(unique, cardinal(0, 1)), modifier(primary, cardinal(0, 1)))
  body invariant: body("expression<bool>", name(optional), cardinal(0, many))
}

declaration query(name: any = name(required), args: any = args(type, cardinal(0, many))) -> type {
  body field: body(type, name(required), cardinal(0, many))
}

declaration compatibilityProjection(name: any = name(required)) {
  body source: body(string, name(forbidden), cardinal(1, 1))
  body gitBlobSha1: body(string, name(forbidden), cardinal(1, 1))
  body role: body(string, name(forbidden), cardinal(1, 1))
}

type string {}
type bool {}
type int {}
type uuid {}
type list {}
type range {}
type json {}
type TypeRef {}
type Id {}
type Page {}

type choice {
  semantic behavior: "choice"
  semantic minArgs: 2
}

type ref {
  semantic behavior: "declaration-ref-kind"
  semantic minArgs: 1
  semantic maxArgs: 1
}

type expression {
  semantic behavior: "expression"
  semantic minArgs: 1
  semantic maxArgs: 1
}

enum NamePolicy {
  case REQUIRED
  case OPTIONAL
  case FORBIDDEN
}

enum CardinalityLabel {
  case OPTIONAL
  case REQUIRED
  case MANY
}

entity CoreEntityExample {
  field id: string @primary
  field state: NamePolicy
  field declarationKind: entity
  invariant: bool
}

query myQuery(id: Id) -> Page<myQuery> {}
