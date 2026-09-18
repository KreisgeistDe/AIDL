# 6. Normative grammar

## Authority

The active AIDL language authority is `spec/core-self-description-v1.aidl`, interpreted through the finite host bootstrap contract in `spec/bootstrap-kernel-v1.json`. This chapter is a deterministic human-readable projection of that authority. It does not independently define declaration kinds, name policies, body slots, cardinalities, modifiers, or type relationships.

`spec/language-surface-v1.json`, revision 4, M10.1/M10.2/M10.3 classification artifacts, and compatibility shells are historical migration/certification evidence after the Breaking Language Reset. They must not be used to admit syntax or semantics into the active language.

<!-- BEGIN GENERATED CORE GRAMMAR -->
Core source SHA-256: `465f22f2a436f6948b4ecb5e01419c922bb0537065fd1d6f5556054ca3dedcbc`

```ebnf
program        = moduleDirective { importDirective } { declaration } ;
moduleDirective= "module" qualifiedName statementEnd ;
importDirective= "import" qualifiedName [ "as" identifier ] statementEnd ;
declaration    = [ "export" ] typeRef identifier [ genericParameters ]
                 [ namedArguments ] [ "->" typeRef ] [ declarationBody ] statementEnd? ;
namedArguments = "(" namedArgument { "," namedArgument } ")" ;
namedArgument  = identifier [ "?" ] ":" ( typeRef | value ) ;
declarationBody= "{" { bodyEntry } "}" ;
bodyEntry      = qualifiedName [ identifier ] [ ":" value ] { modifierCall } statementEnd? ;
modifierCall   = "@" identifier [ "(" [ modifierArgument { "," modifierArgument } ] ")" ] ;
modifierArgument = [ identifier ":" ] value ;
typeRef        = qualifiedName [ "<" typeRef { "," typeRef } ">" ] [ "?" ] ;
```

Concrete declaration contracts are read from `spec/core-self-description-v1.aidl`;
the Bootstrap Kernel owns only the finite structural syntax above.
Current Core-declared kinds/aliases: compatibilityProjection, declaration, entity, enum, query, type.
<!-- END GENERATED CORE GRAMMAR -->

## Core-owned structure

Every declaration uses the same envelope:

`[export] <declaration-type> <identifier> [<generic-parameters>] [(<named-args>)] [-> <result-type>] { ... }`

The Bootstrap Kernel recognizes only structural framing: identifiers and qualified names, literals and expressions, generic/nullable `TypeRef` syntax, named declaration arguments, the arrow result position, body-entry framing, modifier-call tokenization, delimiters, comments, strings and statement termination. It does not contain a concrete declaration-kind catalog.

The direct Core source determines the concrete language contracts. A `declaration` declaration defines a declaration-kind contract. `type` is a Core-authored alias of `declaration`, not a second host type hierarchy. Body entries are interpreted by Core-declared slot contracts, including name policy, value type, cardinality and permitted modifiers. Generic TypeRefs, `ref<...>` and `expression<...>` use the same recursive TypeRef structure; their semantic meaning is Core metadata rather than parser grammar.

## Fail-closed rules

The active Core path fails closed when the Bootstrap Kernel or self-description is inconsistent, a declaration kind has no Core contract, a Core alias is cyclic or shape-incompatible, a TypeRef cannot resolve under Core rules, a body slot is undeclared, a required/forbidden slot name is violated, cardinality is violated, or a modifier is not declared for its slot. Generated semantic meta-IR is accepted only when it is an exact derivation of the direct Core source and declares itself non-authoritative.

`tools/core_language.py` is the P1 authority/substrate entry point. It composes the generic Bootstrap parser, the direct Core compiler, the exact derived semantic registry, and this grammar projection. `tools/core_bootstrap.py` is deliberately independent of `tools/aidl_parser.py` declaration-token tables.

## P2+ migration boundary

Repository-wide source migration is intentionally not part of P1. `tools/aidl_parser.py` and revision-4 classification/compatibility tooling remain temporarily present only to inventory and process the unmigrated historical corpus during the later serial P2+ packages. They are not an active language authority and must not be consulted by the P1 Core parser/semantic path to admit a declaration kind or body slot.

Until P2 migrates a historical source, that source is not evidence that its syntax belongs to the new language. No compatibility alias is introduced by P1 to keep old positive sources valid. Later packages must either migrate those sources to Core-described syntax or retain them solely as explicit rejection/historical evidence.

## Drift checks

`tools.core_language.check_grammar_projection()` requires the generated block in this document to match the exact direct Core source. `load_core_authority()` validates the finite bootstrap firewall before compiling Core, and `validate_core_language_source()` parses with the generic bootstrap grammar and validates semantics derived from the direct Core. P1 tests additionally prove that mutating the legacy parser declaration-kind table cannot change the active Core path.
