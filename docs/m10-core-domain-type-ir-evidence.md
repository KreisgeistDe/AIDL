# M10 Core domain-type IR evidence

This focused M10 closure records executable Canonical-IR evidence for already accepted Core domain type declarations and type constructors.

The Core subset accepts `alias`, `opaque`, `set<T>`, `map<K,V>`, nullable `T?`, and nested combinations of those constructors. Canonical IR materializes an alias's referenced type as `target` and an opaque type's underlying representation as `representation`; every type value uses the closed `typeRef` contract from `spec/ir.schema.json`.

`tools/test_core_domain_type_ir_semantics.py` extends the existing valid M4 minimal source with scalar alias/opaque declarations plus `set` and `map` forms. It builds Canonical IR repeatedly and proves that semantic alias/opaque declaration objects remain deterministic. It also proves that `set<string?>` materializes as `kind: set` with a nullable scalar element, `map<string, uuid?>` materializes as `kind: map` with explicit key/value typeRefs, and `map<string, set<uuid?>>?` preserves both nested constructor shape and outer/inner nullability. The complete emitted document is validated against the closed IR schema.

Negative source evidence proves malformed `set` arity and an invalid `map` key are rejected by existing `AIDL-T001` compiler diagnostics before IR emission. Negative schema evidence proves that emitted `set` and `map` typeRefs must carry their required `element` or `key`/`value` structure.

Before this closure, `tools/compiler_ir.py` routed `set<T>` and `map<K,V>` through the generic `named`/`typeArguments` fallback even though the Core typechecker accepted them and `spec/ir.schema.json` defines dedicated `set` and `map` typeRef variants. `_type` now recognizes only those already accepted constructor names and recursively materializes their existing Core arguments into the dedicated schema shapes; no source syntax or language meaning is widened.

This closure does not promote a whole declaration IR cell: the constructor fix is a cross-cutting Canonical-IR semantic fact used by multiple declaration classes, while `decl.alias`, `decl.opaque`, `decl.value`, and other declaration rows still have independent `partial` Validate/IR/Generate gaps. M10 acceptance criterion 3 is therefore reduced but remains open after rest-gap review, and criterion 1 remains open because multiple required matrix cells are still `partial`. Criteria 2 and 4 remain complete. No generator behavior, IDE support, Ruleset, tag, release, or project `.ai/**` path is changed.
