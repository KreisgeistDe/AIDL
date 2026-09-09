# M16.5 E1 Production Traceability Inventory — Structural-A

Status: **non-normative E1 design evidence**. `docs/06-grammar.md` remains normative. Reference positions are construction metadata only; resolution and target-kind truth remain Semantic-owned. `syntax-default-token` means the production contains the source keyword `default`, not that Structural Schema owns semantic defaulting.

Base: `KreisgeistDe/AIDL@36403b0df688ea46205c0ce015f826dd113c51d9`.

| ID | Source section | Production | Owner | Cardinality | Order | Default relevance | Reference relevance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PF-019 | Programme und Module | `program` | `structural-schema` | repeat | semantic/preserve | none | none |
| PF-020 | Programme und Module | `moduleDecl` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-021 | Programme und Module | `importDecl` | `structural-schema` | optional | preserve | none | reference-position |
| PF-022 | Programme und Module | `exportDecl` | `structural-schema` | single/choice | preserve | none | none |
| PF-023 | Programme und Module | `declaration` | `structural-schema` | single/choice | preserve | none | none |
| PF-024 | App und Profile | `appDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-025 | App und Profile | `appClause` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-026 | App und Profile | `authDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-027 | App und Profile | `a11yDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-028 | App und Profile | `privacyDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-068 | Typdeklarationen | `enumDecl` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-069 | Typdeklarationen | `enumCase` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-070 | Typdeklarationen | `aliasDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-071 | Typdeklarationen | `valueDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-072 | Typdeklarationen | `unionDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-073 | Typdeklarationen | `unionVariant` | `structural-schema` | optional | preserve | none | reference-position |
| PF-074 | Typdeklarationen | `errorDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-075 | Typdeklarationen | `errorClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-076 | Typdeklarationen | `retryClass` | `structural-schema` | single/choice | preserve | none | none |
| PF-077 | Typdeklarationen | `entityDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-078 | Typdeklarationen | `fieldDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-079 | Typdeklarationen | `fieldModifier` | `structural-schema` | single/choice | preserve | syntax-default-token | reference-position |
| PF-080 | Typdeklarationen | `deleteAction` | `structural-schema` | single/choice | preserve | none | none |
| PF-081 | Typdeklarationen | `indexDecl` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-082 | Typdeklarationen | `indexField` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-083 | Typdeklarationen | `invariantDecl` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-084 | Typdeklarationen | `viewDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-085 | Typdeklarationen | `viewMember` | `structural-schema` | optional | preserve | none | reference-position |
| PF-086 | Typdeklarationen | `viewSelection` | `structural-schema` | repeat | semantic/preserve | none | none |
| PF-087 | Typdeklarationen | `viewInlineMember` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-088 | Typdeklarationen | `parameters` | `structural-schema` | repeat | semantic/preserve | none | none |
| PF-089 | Typdeklarationen | `parameter` | `structural-schema` | optional | semantic/preserve | syntax-default-token | reference-position |
| PF-090 | Operationen | `apiDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-091 | Operationen | `apiClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-092 | Operationen | `operationSignature` | `structural-schema` | optional | preserve | none | reference-position |
| PF-093 | Operationen | `policyDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-094 | Operationen | `queryDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-095 | Operationen | `mutationDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-096 | Operationen | `policyStatement` | `structural-schema` | single/choice | preserve | none | none |
| PF-097 | Operationen | `queryClause` | `structural-schema` | single/choice | canonical-only-if-unordered | none | none |
| PF-098 | Operationen | `mutationClause` | `structural-schema` | single/choice | canonical-only-if-unordered | none | none |
| PF-099 | Operationen | `authClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-100 | Operationen | `authMode` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-101 | Operationen | `allowClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-102 | Operationen | `authorizeClause` | `structural-schema` | optional | preserve | none | reference-position |
| PF-103 | Operationen | `errorsClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-104 | Operationen | `timeoutClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-105 | Operationen | `auditClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-106 | Operationen | `callClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-107 | Operationen | `consistency` | `structural-schema` | single/choice | preserve | none | none |
| PF-108 | Operationen | `cacheClause` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-109 | Operationen | `cacheVisibility` | `structural-schema` | single/choice | preserve | none | none |
| PF-110 | Operationen | `idempotencyClause` | `structural-schema` | repeat | preserve | none | none |
| PF-111 | Operationen | `idempotencyInline` | `structural-schema` | single/choice | preserve | none | none |
| PF-112 | Operationen | `idempotencyProperty` | `structural-schema` | single/choice | preserve | none | none |
| PF-113 | Operationen | `transactionBlock` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-114 | Operationen | `isolation` | `structural-schema` | single/choice | preserve | none | none |
| PF-115 | Operationen | `transactionStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-116 | Operationen | `bindingStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-117 | Operationen | `requireStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-118 | Operationen | `writeStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-119 | Operationen | `emitStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-120 | Operationen | `whenStatement` | `structural-schema` | optional + repeats | semantic/preserve | none | none |
| PF-121 | Operationen | `returnStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-122 | Events, Messaging und Verarbeitung | `eventDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-123 | Events, Messaging und Verarbeitung | `topicDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-124 | Events, Messaging und Verarbeitung | `topicClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-125 | Events, Messaging und Verarbeitung | `queueDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-126 | Events, Messaging und Verarbeitung | `queueClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-127 | Events, Messaging und Verarbeitung | `delivery` | `structural-schema` | single/choice | preserve | none | none |
| PF-128 | Events, Messaging und Verarbeitung | `ordering` | `structural-schema` | single/choice | preserve | none | none |
| PF-129 | Events, Messaging und Verarbeitung | `compatibilityMode` | `structural-schema` | single/choice | preserve | none | none |
| PF-130 | Events, Messaging und Verarbeitung | `consumerDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-131 | Events, Messaging und Verarbeitung | `consumerClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-132 | Events, Messaging und Verarbeitung | `invocationKind` | `structural-schema` | single/choice | preserve | none | none |
| PF-133 | Events, Messaging und Verarbeitung | `retryPolicy` | `structural-schema` | optional | preserve | none | none |
| PF-134 | Events, Messaging und Verarbeitung | `namedRetryArgs` | `structural-schema` | repeat | preserve | none | none |
