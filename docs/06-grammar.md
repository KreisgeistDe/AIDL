# 6. Normative grammar

## Authority and support tiers

This chapter is the human-readable grammar projection of the frozen M10.1 language-surface contract in `spec/language-surface-v1.json`, currently revision 4. The JSON contract remains the machine-readable semantic authority if this prose and the contract ever disagree.

The **canonical target language** and **current production admission** are separate concepts. Revision 4 defines the canonical representation for the complete frozen declaration surface, while Production Normalization currently admits only the declaration families certified by M10.1. Canonical syntax therefore does not imply production support. Parser-readable historical spellings are compatibility input only and are not part of the normative target grammar below.

The repository-wide support tiers are:

- **production-admitted canonical** — canonical target syntax with certified Production Normalization evidence;
- **canonical-but-not-yet-admitted** — canonical target syntax frozen by M10.1 but intentionally fail-closed in current production admission;
- **legacy-readable compatibility** — historical source accepted for compatibility and migration, never a second canonical grammar;
- **negative/rejection fixture** — input whose rejection/diagnostic behavior is the evidence;
- **illustrative/aspirational** — explanatory material that does not itself make a production support claim.

`spec/m10-2-language-surface-classification.json` classifies the committed source/documentation corpus into these tiers. M10.3, not this chapter, owns executable migration of intended reference applications and resolution of any product requirement that would need new Python semantics or production admission.

## Canonical program shape

The canonical language uses one uniform declaration envelope:

~~~ebnf
program         = { directive | declaration } ;
directive       = moduleDirective | importDirective ;
moduleDirective = "module" qualifiedName newline ;
importDirective = "import" qualifiedName [ "." "*" ] newline ;

declaration     = { annotation } [ "export" ] kind [ name ]
                  [ headerArguments ] [ "->" typeRef ]
                  "{" { bodySlot } "}" ;
headerArguments = "(" [ namedArgument { "," namedArgument } ] ")" ;
namedArgument   = identifier ":" value ;
bodySlot        = slotKeyword [ slotName ] slotValue newline
                | slotKeyword [ slotName ] "{" { bodySlot } "}" ;
~~~

The exact name policy, permitted header arguments, result-type allowance, body-slot vocabulary, occurrence bounds, ordering, reference-kind constraints and legacy spellings for each declaration are defined by the frozen contract. A spelling not represented by that contract is not added to the target grammar by examples or older prose.

## Frozen canonical declaration kinds

Revision 4 freezes these canonical declaration kinds:

`app`, `auth`, `a11y`, `privacy`, `enum`, `alias`, `value`, `union`, `error`, `entity`, `view`, `api`, `policy`, `query`, `mutation`, `event`, `topic`, `queue`, `consumer`, `projection`, `workflow`, `saga`, `task`, `schedule`, `system`, `service`, `client`, `tenant`, `channel`, `resource`, `media`, `rendition`, `sync`, `migration`, `deployment`, `frontend`, `theme`, `component`, `page`, `form`, `action`, `syncStatus`, `seo`, `nativeFunction`, `nativeComponent`, `fixture`, `test`, and `scenario`.

Only the M10.1-certified subset is production-admitted today. All other canonical kinds remain fail-closed until an explicit versioned admission decision and certification says otherwise.

## Canonical forms with revision-4 structural detail

The following forms are normative projections of contract-owned structure, not independent language rules.

### App

~~~ebnf
appDecl      = [ "export" ] "app" identifier "{" profileSlot { profileSlot } "}" ;
profileSlot  = "profile" identifier "{" "version" integer "}" ;
~~~

### Enum

Canonical enum members are explicit `case` slots:

~~~ebnf
enumDecl = [ "export" ] "enum" identifier "{" caseSlot { caseSlot } "}" ;
caseSlot = "case" identifier [ "=" literal ] newline ;
~~~

Comma-separated bare enum cases are legacy-readable compatibility syntax only.

### Alias

~~~ebnf
aliasDecl = [ "export" ] "alias" identifier "=" typeRef newline ;
~~~

`opaque Name = Type` is a legacy alias spelling, not a canonical declaration kind.

### Entity

Canonical entity members use explicit semantic slots:

~~~ebnf
entityDecl = [ "export" ] "entity" identifier "{" { fieldSlot | indexSlot } "}" ;
fieldSlot  = "field" identifier ":" typeRef { fieldModifier } newline ;
indexSlot  = "index" identifier slotValue newline ;
~~~

Unprefixed `name: Type` entity members are compatibility input only.

### Query and mutation

~~~ebnf
queryDecl    = [ "export" ] "query" identifier [ parameterList ] "->" typeRef
               "{" { querySlot } "}" ;
mutationDecl = [ "export" ] "mutation" identifier [ parameterList ] "->" typeRef
               "{" { mutationSlot } "}" ;
parameterList = "(" [ parameter { "," parameter } ] ")" ;
parameter     = identifier ":" typeRef [ "default" value ] ;
querySlot     = "read" value newline
              | "allow" value newline
              | "errors" typeRefList newline
              | "timeout" duration newline ;
mutationSlot  = "allow" value newline
              | "errors" typeRefList newline
              | "call" value newline
              | "audit" value newline
              | "timeout" duration newline ;
~~~

Legacy operation source may contain additional readable clauses. Clauses not represented by revision-4 BodySlots remain explicit fail-closed compatibility facts; they are not normative target slots merely because the parser can read them.

### Consumer, projection, client, migration

These families use named canonical header arguments rather than positional special-case headers:

~~~ebnf
consumerDecl   = [ "export" ] "consumer" identifier
                 "(" "topic" ":" declarationRef "," "messageType" ":" typeRef ")"
                 "{" { bodySlot } "}" ;
projectionDecl = [ "export" ] "projection" identifier
                 "(" "sources" ":" typeRef "," "target" ":" declarationRef ")"
                 "{" { bodySlot } "}" ;
clientDecl     = [ "export" ] "client" identifier
                 "(" "service" ":" declarationRef ")" "{" { bodySlot } "}" ;
migrationDecl  = [ "export" ] "migration" identifier
                 "(" "fromVersion" ":" string "," "toVersion" ":" string ")"
                 "{" { bodySlot } "}" ;
~~~

Historical `on/from`, `from/into`, `for`, and `from "a" to "b"` headers are compatibility spellings only.

## Type references, modifiers, annotations and cardinality

The canonical type-reference model is contract-owned. A TypeRef carries its base kind/name plus optionality and only the modifiers frozen by revision 4. M10.1 certification proves current production parity for the admitted TypeRef/reference-projection facts and fail-closed behavior for unsupported generic/non-range constraint shapes.

Annotations are source metadata only where the frozen contract permits them; an annotation does not create a new declaration or body-slot meaning. Occurrence/cardinality is defined per contract node through `min`/`max`, including required singleton slots, optional singletons and ordered repeated slots. Documentation must not replace those bounds with a looser parser-oriented rule.

## Compatibility grammar is non-normative

The Python parser intentionally remains able to read historical source forms required for compatibility and migration evidence. Those forms include, among others, bare enum cases, `opaque` aliases, unprefixed entity fields, positional operation/consumer/projection/client/migration headers, and legacy clauses whose facts are rejected by current Production Normalization.

Compatibility readability is not production admission and not a permanent parallel grammar. Existing reference applications and compatibility fixtures remain in that source form during M10.2 and are classified explicitly. M10.3 owns their intended migration/disposition.

## Validation and drift

`python3 -m tools.m10_2_language_surface_classification` deterministically inventories every committed `.aidl` file and validates the required documentation classification against frozen revision 4. New unclassified source files, duplicate source-rule matches, document-index drift, classification-vocabulary drift, or frozen-contract identity drift fail closed. Focused negative regressions live in `tools/test_m10_2_language_surface_classification.py`.
