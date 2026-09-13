module aidl.core.self

// P3 normative direct self-description. The finite host understands only the
// structural meta-combinators; concrete declaration kinds are declared here.
declaration declaration(name: name(required), args: args(cardinal(0, many))) {
  body body: body(name(required), cardinal(0, many))
}

declaration type(name: name(required), args: args(cardinal(0, many)), produces: produces(type)) {
  body semantic: body(name(required), cardinal(0, many))
}

declaration enum(name: name(required), produces: produces(type)) {
  body case: body(name(required), cardinal(1, many))
}

declaration entity(name: name(required)) {
  body field: body(type-position, "choice<TypeRef, ref<entity>>", name(required), cardinal(0, many), modifier(unique, cardinal(0, 1)), modifier(primary, cardinal(0, 1)))
  body invariant: body(type-position, "expression<bool>", name(optional), cardinal(0, many))
}

declaration compatibilityProjection(name: name(required)) {
  body source: body(string, name(forbidden), cardinal(1, 1))
  body gitBlobSha1: body(string, name(forbidden), cardinal(1, 1))
  body role: body(string, name(forbidden), cardinal(1, 1))
}

// Visible base and generic carrier names originate from AIDL definitions.
type string {}
type bool {}
type int {}
type uuid {}
type list {}
type range {}
type json {}
type TypeRef {}

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

// enum is not a host special case. Its declaration-kind contract produces(type),
// therefore every named enum instance is a valid type carrier by the same rule.
enum NamePolicy {
  case REQUIRED:
  case OPTIONAL:
  case FORBIDDEN:
}

enum CardinalityLabel {
  case OPTIONAL:
  case REQUIRED:
  case MANY:
}

// Direct self-described proof: the host has no concrete knowledge of entity.
entity CoreEntityExample {
  field id: string @primary
  field state: NamePolicy
  invariant: bool
}
