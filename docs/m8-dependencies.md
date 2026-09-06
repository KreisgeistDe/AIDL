# M8 — Declaration dependencies

`aidl dependencies <FQN>` gives coding agents a compact, deterministic view of the declarations directly and transitively referenced by one compiler-owned declaration.

## Usage

```text
aidl dependencies <FQN> [PATH ...]
aidl dependencies <FQN> [PATH ...] --format json
```

`<FQN>` is an exact compiler-owned fully qualified declaration name such as `demo.getPet`. `PATH` accepts AIDL files or directories and defaults to the current directory.

Human output remains the compact direct-dependency view for compatibility. JSON output uses the current versioned CLI schema and distinguishes direct from transitive results explicitly.

## Semantic boundary

The command does not parse source text to guess references and does not consult IntelliJ PSI. It first resolves the requested FQN through the existing M8-02 compiler inspection boundary. For a uniquely resolved declaration, it uses Canonical IR and the existing M8-03 direct relation: values inside a canonical declaration node count as edges only when they are declaration IDs already present in the same Canonical IR document.

M8-08 defines transitivity only as the cycle-safe reachability closure over that exact direct relation. No source-only relationship, repository heuristic, language rule, extra reference kind, or change-impact inference is added.

The JSON result separates:

- `dependencies`: direct M8-03 dependencies only;
- `transitiveDependencies`: reachable dependencies at depth two or greater, excluding anything already direct;
- `totals`: complete direct/transitive counts before bounding;
- `truncated`: per-list truncation flags.

The target declaration is never returned as its own dependency, including when the Canonical-IR graph contains a cycle back to the target. Duplicate paths collapse to one declaration identity. Both lists are sorted by FQN, then kind, then declaration ID.

Each direct or transitive dependency contains only:

- `fullyQualifiedName`;
- `kind`;
- `declarationId`.

## Bounds and determinism

Direct and transitive lists are independently bounded to 128 identities. `totals.directDependencies` and `totals.transitiveDependencies` always report the full pre-bound counts, while `truncated.directDependencies` and `truncated.transitiveDependencies` say whether the corresponding list was shortened.

Traversal is cycle-safe and does not depend on source order. Final projection order is stable, so identical compiler/Canonical-IR input produces byte-for-byte deterministic JSON.

## JSON result

A successful result has `status = "resolved"` and contains:

```json
{
  "status": "resolved",
  "query": "demo.getPet",
  "declaration": {
    "declarationId": "demo.getPet@1",
    "fullyQualifiedName": "demo.getPet",
    "kind": "query"
  },
  "dependencies": [
    {
      "declarationId": "demo.PetService@1",
      "fullyQualifiedName": "demo.PetService",
      "kind": "service"
    }
  ],
  "transitiveDependencies": [
    {
      "declarationId": "demo.Pet@1",
      "fullyQualifiedName": "demo.Pet",
      "kind": "entity"
    }
  ],
  "totals": {
    "directDependencies": 1,
    "transitiveDependencies": 1
  },
  "truncated": {
    "directDependencies": false,
    "transitiveDependencies": false
  }
}
```

The normal CLI envelope adds `command`, `diagnostics`, and `ok` around this result.

## Failure behavior and exit codes

Expected failures exit `1`:

- syntactically invalid FQN: `result.status = "invalid"`, `error.kind = "invalidFqn"`;
- syntactically valid but missing FQN: `result.status = "unknown"`, `error.kind = "unknownFqn"`;
- duplicate compiler symbols for the same FQN: `result.status = "ambiguous"`, `error.kind = "ambiguousFqn"`;
- compiler errors in the project: `error.kind = "compiler"` with unchanged compiler diagnostics;
- inability to build the existing Canonical IR dependency view: `error.kind = "dependencyBuild"`.

Success exits `0`. Unexpected internal failures remain exit `70` and use the existing machine-readable `internal` error path.

## Schema compatibility

M8-03 introduced the direct-only `aidl dependencies` envelope in frozen `spec/cli-output-v3.schema.json`. M8-08 advances the current closed contract to `spec/cli-output-v7.schema.json`, preserving frozen v1-v6 artifacts unchanged. V7 accepts the prior v6 contract by reference and adds the extended bounded dependencies result only.

The direct `dependencies` field keeps its M8-03 meaning. The new transitive fields are additive in the current schema generation; prior closed schema generations continue to reject the extended payload by design.
