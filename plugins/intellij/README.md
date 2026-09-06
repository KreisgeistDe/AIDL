# AIDL IntelliJ Plugin

IntelliJ Platform plugin for AIDL as described in `../../docs/06-grammar.md`.

## Features

- Registers `.aidl` files as AIDL files.
- Provides lexer-based syntax highlighting for declarations, scalar types, literals, comments, annotations, operators and punctuation from the normative grammar.
- Provides a permissive parser definition so files get an AIDL PSI root and can be opened, indexed and highlighted without generated Grammar-Kit sources.
- Provides a compiler-diagnostics adapter that executes `aidl check <project> --format json` and maps the compiler-owned diagnostic code, phase, severity, message, source location and `allowedFixes` metadata into plugin-side data objects without duplicating semantic rules in PSI/Kotlin.
- Registers an AIDL local inspection that runs the compiler adapter for the IntelliJ project, filters diagnostics to the current file, maps compiler severity and source positions to editor problems, and keeps the diagnostic code and message visible.
- Offers IntelliJ Quick Fixes only when the compiler explicitly emits a supported `allowedFixes` entry. The current safe edit boundary supports compiler-owned `insertClause` fixes and uses the compiler-provided fix text unchanged.
- Resolves Go to Definition through the compiler-owned `aidl resolve <project> --file <file> --offset <offset> --format json` boundary. The compiler identifies the lexical reference and resolves local, imported and fully qualified declaration names through its existing symbol/import tables; IntelliJ only maps the returned file/source location back to PSI.
- Finds usages through `aidl usages <project> --file <file> --offset <offset> --format json`. The compiler reuses the same unique-target reference semantics and returns deterministic file/source locations; IntelliJ maps only those returned locations to AIDL references.
- Performs declaration Rename through `aidl rename <project> --file <file> --offset <offset> --new-name <name> --apply --format json`. The compiler owns identifier validation, collision checks, the complete declaration/reference edit set, copied-project preflight validation, application with rollback, and final compiler revalidation.
- Provides BASIC completion through `aidl complete <project> --file <file> --offset <offset> --format json`. The compiler derives a safe partial reference and returns deterministic local/imported/qualified candidates using the existing symbol table/import-resolution semantics; IntelliJ only renders those compiler-returned candidates.
- Provides Hover/Quick Documentation through `aidl document <project> --file <file> --offset <offset> --format json`. Declaration/reference docs reuse compiler symbol resolution and return FQN, declaration kind, declaration source location and a compact compiler-derived declaration header; diagnostic docs preserve the compiler-owned `code`, `phase`, `severity`, `message`, `subject`, `expected`, `docs` and `allowedFixes` fields unchanged.

The diagnostics adapter treats language diagnostics as normal successful adapter output even when `aidl check` exits with validation status `1`. Compiler-internal failures, process failures and malformed/inconsistent JSON responses are returned as distinct failure kinds and are not surfaced by the inspection as invented language diagnostics.

Inspection source mapping uses a valid compiler offset when available and falls back to the compiler line/column for the same file. Diagnostics for other files or positions that cannot be mapped safely are ignored for the current editor inspection. Quick Fixes are likewise suppressed for foreign files, unsafe edit positions, unknown fix kinds, absent `allowedFixes`, and adapter failures; the IDE never derives fixes from diagnostic codes or PSI-local language rules.

For the currently supported compiler `insertClause` metadata, the editor inserts the exact compiler-supplied clause text only when the mapped diagnostic line has a safely identifiable opening brace.

Reference navigation no longer uses `AidlPsiUtil` declaration/import matching as semantic resolution. `AidlReference.resolve()` accepts only a unique compiler target. Unresolved or ambiguous compiler results, invalid/foreign locations, malformed JSON and process/compiler failures produce no guessed navigation target.

Find Usages and Rename extend that same compiler-owned boundary. Usage discovery returns no guessed hits for unresolved, ambiguous or invalid targets or infrastructure/JSON failures. Rename is deliberately conservative: it is available only for compiler-resolved declaration names; keyword/invalid identifiers, FQN collisions, projects with existing compiler errors, unsafe source edits, failed preflight compilation, or failed post-apply compiler validation are rejected without leaving a partial rename. IntelliJ does not derive a usage set or collision rules from PSI.

Completion also preserves compiler ownership. Unqualified candidates come only from the current compiler module and its already-resolved exact/wildcard imports; ambiguous simple names are omitted. Qualified candidates come only from the compiler FQN symbol table. Parser-unproven/lexically unsafe positions and process/compiler/JSON failures produce no semantic completion items. Kotlin/PSI does not maintain a parallel visibility, import or type rule table.

Documentation preserves the same boundary. IntelliJ sends only the project path, source file and offset to `aidl document`, then renders only compiler-returned fields. Unresolved, ambiguous, invalid or foreign positions and process/compiler/JSON failures produce no guessed declaration docs. Diagnostic explanation text is not synthesized in Kotlin/PSI: the compiler's existing message/expected/docs/allowedFixes data remains authoritative.

The default adapters expect `aidl` on `PATH`; callers may inject another executable command and process runner, which also keeps adapter tests independent from a locally installed compiler.

## Build

```bash
./gradlew check
./gradlew buildPlugin
```

The build uses the IntelliJ Platform Gradle Plugin 2.x and targets IntelliJ IDEA Community `2026.2.0.1`.
