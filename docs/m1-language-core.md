# M1 Language Core completion

M1 is the compiler-owned project parsing, naming and diagnostic boundary beneath later semantic, IR, generator and IDE layers.

## Implemented boundary

The project parser discovers UTF-8 `.aidl` sources deterministically and produces parser-owned nodes with source spans. `tools/compiler_ast.py` projects those nodes into a typed compiler document/declaration boundary that is independent of IntelliJ PSI. `tools/compiler_project.py` builds module indexes, declaration FQNs, exact and wildcard import resolutions, module dependency cycles and deterministic declaration/operation symbol tables.

The production `aidl check` path reports stable, source-located M1 diagnostics:

- `AIDL-P001` — parser failure;
- `AIDL-R001` — unresolved import;
- `AIDL-R002` — duplicate declaration;
- `AIDL-R003` — unresolved declaration name in a Core reference position;
- `AIDL-R004` — cyclic module dependency.

`AIDL-R003` is deliberately conservative. It covers already parsed Core reference positions whose declaration meaning is established by the existing compiler project model: named type expressions, operation parameter/return types, declared errors, service ownership/resources/operation bindings, API operation bindings, consumer event/topic references and transaction resources. It does not scan arbitrary identifiers or invent new name-resolution semantics.

`AIDL-R004` is derived only from the existing deterministic module dependency SCCs. The diagnostic is anchored to the first module declaration in stable project order and renders the complete cycle path.

Both diagnostics use the existing explicit compiler severity contract and flow through the existing human and JSON `aidl check` surfaces. Later M2+ policy diagnostics remain unchanged.

## Independence from IntelliJ

Compiler/parser semantics live under `tools/` and do not import IntelliJ or PSI classes. IntelliJ adapters consume compiler CLI/results; editor behavior is not the source of parsing, name resolution or diagnostics.

## Validation

M1 completion is covered by the existing parser, compiler AST/project, resolution, contextual-keyword and diagnostic suites plus focused `aidl check` regressions for unresolved names and module cycles. Repository CI continues to run the production compiler suite, spec lint, Petstore parser/check boundaries, Golden Fixtures, Petstore runtime and IntelliJ checks.

The roadmap completion marks only behavior demonstrated by source and regression coverage; it does not promote deferred language features or add M8 tooling.