module aidl.core

declaration NamePolicy(kind: "meta") {
  body values: ["required", "optional", "forbidden"] @ordered
}

declaration Cardinality(kind: "meta") {
  body min: int @required
  body max: int?
  body optional: {min: 0, max: 1}
  body required: {min: 1, max: 1}
  body variadic: {min: 0, max: null}
}

declaration TypeRef(kind: "meta") {
  body name: string @required
  body arguments: list<TypeRef>
  body optional: bool
  body examples: ["ref<entity>", "expression<bool>", "range<int>", "list<ref<entity>>?"] {
    @ordered
  }
}

declaration ArgumentDefinition(kind: "meta") {
  body name: string @required
  body type: TypeRef @required
  body cardinality: Cardinality @required
}

declaration ModifierDefinition(kind: "meta") {
  body name: string @required
  body targets: list<string> @required
  body arguments: list<ArgumentDefinition>
  body cardinality: Cardinality @required
}

declaration BodySlotDefinition(kind: "meta") {
  body bodyType: string @required
  body namePolicy: NamePolicy @required
  body valueType: TypeRef?
  body cardinality: Cardinality @required
  body ordered: bool
  body uniqueByName: bool
  body modifiers: list<ModifierDefinition>
}

declaration DeclarationDefinition(kind: "meta") {
  body kind: string @required
  body namePolicy: NamePolicy @required
  body arguments: list<ArgumentDefinition>
  body result: TypeRef?
  body slots: list<BodySlotDefinition>
  body modifiers: list<ModifierDefinition>
}

declaration MetaCombinatorDefinition(kind: "meta") {
  body behavior: string @required
  body arguments: Cardinality @required
}

declaration SemanticMetaModel(kind: "meta") {
  body categoryArgument: "kind" @required
  body categories: {"meta-combinator": MetaCombinatorDefinition, "modifier": ModifierDefinition, "language": DeclarationDefinition} @required
  body ignoredCategories: ["meta", "bootstrap"] @required
}

declaration declaration(kind: "bootstrap") {
  body namePolicy: "required" @required
  body framing: "[export] <kind> [identifier] [(named-args)] [-> <typeRef>] { <body-entries>* }"
}

declaration body(kind: "bootstrap") {
  body forms: {
    ["inline", "multiline-v1", "multiline-v2"]
    @ordered
  }
  body modifierBoundary: "@"
}
