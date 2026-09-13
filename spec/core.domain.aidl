module aidl.core.domain
import aidl.core

// Core-owned semantic combinators. The host semantic engine dispatches by the
// declared behavior value; domain declaration names are never hard-coded.
declaration choice(kind: "meta-combinator") {
  body behavior: "choice"
  body arguments: {min: 2, max: null}
}

declaration ref(kind: "meta-combinator") {
  body behavior: "declaration-ref-kind"
  body arguments: {min: 1, max: 1}
}

declaration expression(kind: "meta-combinator") {
  body behavior: "expression"
  body arguments: {min: 1, max: 1}
}

declaration primary(kind: "modifier") {
  body targets: ["field"]
  body arguments: []
  body cardinality: {min: 0, max: 1}
}

declaration unique(kind: "modifier") {
  body targets: ["field"]
  body arguments: []
  body cardinality: {min: 0, max: 1}
}

declaration entity(kind: "language") {
  body namePolicy: "required"
  body arguments: []
  body result: null
  body slots: [
    {
      bodyType: "field",
      namePolicy: "required",
      valueType: choice<TypeRef, ref<entity>>,
      cardinality: {min: 0, max: null},
      ordered: true,
      uniqueByName: true,
      modifiers: ["primary", "unique"]
    },
    {
      bodyType: "invariant",
      namePolicy: "optional",
      valueType: expression<bool>,
      cardinality: {min: 0, max: null},
      ordered: true,
      uniqueByName: true,
      modifiers: []
    }
  ]
  body modifiers: []
}
