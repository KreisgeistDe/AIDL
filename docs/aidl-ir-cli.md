# `aidl ir` — Canonical IR CLI

## Scope

M3-08 adds the first production compiler CLI surface: `aidl ir <path> [<path> ...]`.
The command accepts AIDL files or directories, reuses deterministic source discovery,
loads the existing compiler analysis, and emits the canonical AIDL JSON IR defined by
`spec/ir.schema.json`.

This task implements only `aidl ir`. `aidl plan`, production `aidl check`, common JSON
command envelopes, and general CLI exit-code conventions remain later M3 work.

## Pipeline

`tools/aidl_cli.py` drives the command and `tools/compiler_ir.py` owns the compiler-side
source-to-IR projection. The producer composes the existing M3 contracts rather than
redefining them:

1. parse, project, resolve, and run the existing compiler diagnostics/semantic checks;
2. refuse IR emission when any compiler diagnostic has `error` severity;
3. derive declaration identity through the M3-03 `declaration_identity` boundary;
4. project supported Core declaration, operation, topology, deployment, profile, and
   source-map semantics into the closed M3-01 IR shape;
5. run the M3-05 semantic projection, which also materializes M3-04 defaults;
6. fill M3-07 declaration/document semantic hashes;
7. serialize stdout through the M3-02 canonical JSON text contract.

The producer requires exactly one `app` declaration and exactly one `system`
declaration. API/event majors use their explicit source major where available; other
IR declaration identities continue to use the explicit M3-03 major `1` because the
source model has no separate authoritative declaration-major contract yet.

Profile-specific producer mappings are not invented by M3-08. Active profile IDs and
majors are retained from the app declaration, while `profileExtensions` is emitted as
an empty object until a profile task defines and implements a source-to-extension
projection.

## Output contract

On success, stdout contains only canonical JSON and exactly one trailing LF. The output
includes `irVersion: "0.3.0"`, deterministic declaration/document `semanticHash`
values, stable declaration identities, semantic defaults, topology/deployments, and a
source map. Re-running the command over identical semantic input produces the same
canonical bytes, subject to the existing M3-02 ordering contract.

Compiler diagnostics and IR build errors are written to stderr. If compiler analysis
contains an error, the command emits no IR on stdout and returns non-zero. M3-08 does
not define the repository-wide final exit-code taxonomy for all future CLI commands.

## Entrypoints

The repository-root `aidl` executable delegates to `tools.aidl_cli.main`:

```bash
./aidl ir path/to/project
```

The Python module can also be invoked directly for development/testing:

```bash
python3 -m tools.aidl_cli ir path/to/project
```

## Validation

`tools/test_aidl_ir.py` verifies schema-valid deterministic source-to-IR production,
M3-04/M3-07 composition, canonical stdout, and diagnostic failure behavior. The Python
validation workflow runs those focused tests alongside M3-01..07 regressions, the full
Python suite, repository spec lint, and the existing Petstore parser smoke.

The Petstore parser smoke intentionally remains a parser-level repository smoke because
the wider Petstore tree includes deferred UI sources with known unresolved standard-UI
imports and a duplicate UI declaration. M3-08 does not weaken compiler error gating or
reinterpret deferred UI/profile semantics to make that wider fixture compile.
