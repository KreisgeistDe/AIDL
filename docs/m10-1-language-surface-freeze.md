# M10.1 Normative Language Surface Freeze

**Status:** accepted target design for review; normative for post-freeze front-end work once merged.

**Decision:** AIDL has one canonical semantic construction model for the next front end. Existing `docs/06-grammar.md` remains the accepted legacy source grammar until a versioned migration implementation lands, but parser-specific legacy shapes are not allowed to define the new Kotlin AST/IR model.

The canonical declaration direction is:

```text
[export] <kind> <name?> [(named-args)] [-> type] { slots }
```

The exact machine-readable contract is `spec/language-surface-v1.json`, validated by `spec/language-surface-v1.schema.json`. The roadmap authority and sequencing rules are in `backlog/m10-1-language-freeze.md`.

## Metamodel semantics

### DeclarationKind and NamePolicy

A `DeclarationKind` has a stable semantic kind ID, `NamePolicy(required|optional|none)`, optional named header arguments, optional result type and typed body slots. Name presence is checked from `NamePolicy`, never from an incidental parser production. `auth`, `a11y`, and `privacy` demonstrate `none`; ordinary named declarations demonstrate `required`. The metamodel supports `optional` even when no current declaration needs that policy, so the semantic choice is explicit rather than encoded as parser branching.

### HeaderArgs

Header arguments are named semantic facts. `args?` means exactly that the parenthesized argument-list form has metamodel occurrence `min=0,max=1`. Each argument has its own occurrence. Positional legacy forms such as `migration M from "1" to "2"`, `client C for Service`, `consumer C on Topic from Event`, and `projection P from [A] into Store` normalize to named arguments before canonical IR.

### BodySlot

Every body member is a `BodySlot` with a stable ID, visible keyword (which may be absent in legacy source), `NamePolicy`, explicit occurrence `{min,max}`, order contract, uniqueness flag, value mode, and optional nested slots. `A*` is only shorthand for occurrence `{min:0,max:null}` and `R?` only for `{min:0,max:1}`. They never imply list/reference/type optionality. Shared block-body semantics are recursive `BodySlot` containers; context-specific schemas preserve domain meaning.

### TypeRef, T? and ReferenceProjection

`T?` means only `TypeRef.optional=true`. Collection size and slot occurrence are separate facts. A reference type is structured as target declaration plus optional projection and resolved projected type. Thus `Pet.id` is represented as `target=Pet`, `projection=id`, and (after resolution) the actual type of `Pet.id`; it is not retained as an opaque dotted string. Range constraints similarly carry explicit `min` and `max` facts.

### ModifierCall

A modifier/annotation call has a stable name, allowed target set, explicit argument arity `{min,max}`, and argument value mode. `@publicReason("...")` on `query getPet` is therefore a one-argument literal-valued call targeting `query`; applying it to an unsupported target or with the wrong arity is invalid independent of token parsability. Field modifiers follow the same contract model.

### Literal versus expression

`value_mode=literal` accepts only the declared literal category and never silently enters expression resolution. `value_mode=expression` is parsed and type-checked as an expression and may contain names, member access, operators, calls, lists or objects according to the expression grammar. `type_ref`, `declaration_ref`, `block`, and `enum_case` are separate modes. This boundary is normative because moving a slot between literal and expression changes semantics and diagnostics.

### Enum

Enum cases are first-class `enum_case` body slots: required unique case name, optional explicit wire literal, source-order preservation. They are not generic identifiers or arbitrary expressions.

## Canonical / legacy / remove inventory

All 48 current declaration kinds remain canonical semantic kinds. `module` and `import` remain canonical file directives. The contract records special legacy spellings where a declaration-specific header or body shape currently carries semantic facts.

**Legacy:** fixed relationship words in declaration headers, operation-signature positional shape, unprefixed entity fields, comma-only enum case construction, `opaque` as an alias spelling, and `ref Qualified.Name` as a source spelling. They remain accepted only under the selected legacy language version until the migration lifecycle removes them.

**Remove from canonical surface, preserve semantics:** declaration-specific positional relationship syntax; body-slot identity inferred solely from parser context; overloaded `?/*` cardinality notation outside its proper layer; unresolved dotted reference projections; and untyped modifier tails. These are removed as canonical *construction mechanisms*, not as semantic facts.

**Canonical:** named header facts, explicit typed body slots, structured TypeRef/ReferenceProjection, ModifierCall contracts, enum-case slots, and the common declaration framing above.

There is no source-form fork with two independently evolving semantics. The only compatibility path is versioned legacy parse -> canonical AST/IR -> canonical formatter/migrator. For syntax-only migrations, legacy and canonical sources must converge on identical normalized IR and semantic hash.

## Relation to M16.5 and M10.5

M16.5 E1/E2 records remain useful evidence for kernel boundaries, migration discipline and evaluation methodology, but their target shapes are no longer merely free-standing candidates where this ADR makes a decision. M10.1 is the design authority; M16.5 becomes the downstream evaluation/tooling/adoption gate. A later proposal that changes the frozen model requires a new versioned language decision, M7 compatibility classification, migration plan and evidence.

M10.1 is sequenced after completed M10 Core conformance and before M10.5. M10.5-01/-02 may continue where work is genuinely language-neutral and the existing M10.5 roadmap allows it. M10.5-03 parser/source-projection and later IR ownership are blocked on this freeze and must implement this canonical model while preserving the legacy compatibility corpus. M10.5, not M11.5, is the Kotlin compiler-core migration gate. This package intentionally does not perform the broad parser/AST/resolver/typechecker migration.

## Consequences and next step

The next sequential M10.1 package is the compatibility bridge: introduce the canonical in-memory model and normalization layer behind the existing parser, map representative legacy forms into it, compute normalized semantic hashes, and add a formatter/migrator prototype without changing default accepted syntax. Only after that evidence is green should Kotlin M10.5-03 front-end slices encode the frozen model.
