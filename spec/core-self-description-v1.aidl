module aidl.core.self

// P2 normative direct self-description. The finite host understands only the
// structural meta-combinators; concrete declaration kinds are declared here.
declaration declaration(args: args(cardinal(0, many))) {
  body body: body(name(required), cardinal(0, many))
}

declaration type(args: args(cardinal(0, many)), produces: produces(type)) {
}

declaration enum(produces: produces(type)) {
  body case: body(name(required), cardinal(1, many))
}

declaration entity {
  body field: body(type-position, name(required), cardinal(0, many), modifier(unique, cardinal(0, 1)), modifier(primary, cardinal(0, 1)))
  body invariant: body(bool, name(optional), cardinal(0, many))
}

// Visible base and generic carrier names originate from AIDL definitions.
type string {}
type bool {}
type int {}
type uuid {}
type list {}
type range {}
type ref {}
type expression {}

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
