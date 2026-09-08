# M16.5 E1 Production Traceability Inventory — Kernel

Status: **non-normative E1 design evidence**. `docs/06-grammar.md` remains normative. Each row assigns exactly one construction authority owner; reference target truth and semantic defaults remain Semantic-owned.

Base: `KreisgeistDe/AIDL@36403b0df688ea46205c0ce015f826dd113c51d9`.

| ID | Source section | Production | Owner | Cardinality cue | Order contract | Default relevance | Reference relevance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PF-001 | Lexikalische Regeln | `letter` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-002 | Lexikalische Regeln | `digit` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-003 | Lexikalische Regeln | `identifier` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-004 | Lexikalische Regeln | `typeName` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-005 | Lexikalische Regeln | `upperLetter` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-006 | Lexikalische Regeln | `qualifiedName` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-007 | Lexikalische Regeln | `integer` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-008 | Lexikalische Regeln | `decimalLiteral` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-009 | Lexikalische Regeln | `percentage` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-010 | Lexikalische Regeln | `durationLiteral` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-011 | Lexikalische Regeln | `byteLiteral` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-012 | Lexikalische Regeln | `cpuLiteral` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-013 | Lexikalische Regeln | `number` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-014 | Lexikalische Regeln | `string` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-015 | Lexikalische Regeln | `regex` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-016 | Lexikalische Regeln | `comment` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-017 | Lexikalische Regeln | `annotation` | `kernel` | optional cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-018 | Lexikalische Regeln | `newline` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-029 | Typen | `type` | `kernel` | optional cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-030 | Typen | `primaryType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-031 | Typen | `scalarType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-032 | Typen | `namedType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-033 | Typen | `constrainedType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-034 | Typen | `genericType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-035 | Typen | `listType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-036 | Typen | `refType` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-037 | Typen | `recordType` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-038 | Typen | `recordField` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-039 | Typen | `inlineEnumType` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-040 | Typen | `typeArguments` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-041 | Typen | `typeParameters` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-042 | Typen | `typeParameter` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-043 | Typen | `typeBound` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-044 | Typen | `constraintArguments` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-045 | Typen | `constraintArgument` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-046 | Typen | `range` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-047 | Ausdrücke | `expression` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-048 | Ausdrücke | `orExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-049 | Ausdrücke | `andExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-050 | Ausdrücke | `equalityExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-051 | Ausdrücke | `relationalExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-052 | Ausdrücke | `additiveExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-053 | Ausdrücke | `multiplicativeExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-054 | Ausdrücke | `unaryExpression` | `kernel` | optional cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-055 | Ausdrücke | `postfixExpression` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-056 | Ausdrücke | `memberAccess` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-057 | Ausdrücke | `callSuffix` | `kernel` | optional cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-058 | Ausdrücke | `indexSuffix` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-059 | Ausdrücke | `primaryExpression` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-060 | Ausdrücke | `arguments` | `kernel` | repeat cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-061 | Ausdrücke | `argument` | `kernel` | optional cue | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-062 | Ausdrücke | `spread` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-063 | Ausdrücke | `listLiteral` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-064 | Ausdrücke | `objectLiteral` | `kernel` | optional + repeat cues | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |
| PF-065 | Ausdrücke | `objectMember` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-066 | Ausdrücke | `capabilityLiteral` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | kernel name/type shape; resolution truth is Semantic |
| PF-067 | Ausdrücke | `literal` | `kernel` | single/choice | kernel-defined evaluation/sequence | no structural default; semantic defaults stay Semantic | none evident in production shape |

Kernel contains 57/57 Cycle-4 productions. No declaration/body vocabulary is Kernel-owned.
