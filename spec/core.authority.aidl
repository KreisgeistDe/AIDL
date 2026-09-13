module aidl.core.authority
import aidl.core

// G1 authority plumbing is itself Core-authored data. A compatibility
// projection may describe legacy semantics only when an exact artifact digest
// is bound here and validated before production normalization consumes it.
declaration compatibilityProjection(kind: "language") {
  body namePolicy: "required"
  body arguments: []
  body result: null
  body slots: [
    {
      bodyType: "source",
      namePolicy: "forbidden",
      valueType: string,
      cardinality: {min: 1, max: 1},
      ordered: true,
      uniqueByName: false,
      modifiers: []
    },
    {
      bodyType: "gitBlobSha1",
      namePolicy: "forbidden",
      valueType: string,
      cardinality: {min: 1, max: 1},
      ordered: true,
      uniqueByName: false,
      modifiers: []
    },
    {
      bodyType: "role",
      namePolicy: "forbidden",
      valueType: string,
      cardinality: {min: 1, max: 1},
      ordered: true,
      uniqueByName: false,
      modifiers: []
    }
  ]
  body modifiers: []
}
