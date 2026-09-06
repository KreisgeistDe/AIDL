# AGENTS.md

## Scope

These instructions apply to the IntelliJ plugin in this directory.

## Project

This is the IntelliJ Platform plugin for AIDL described in:

- `../../docs/06-grammar.md`
- `../../spec/profile-registry.json`
- `../../spec/ir.schema.json`

The example projects under `../../examples/` are useful regression fixtures, especially:

- `../../examples/calendar-offline/app.aidl`
- `../../examples/petstore/app.aidl`
- `../../examples/videohub/app.aidl`

## Build

Use the Gradle wrapper from this directory:

```bash
./gradlew check
./gradlew buildPlugin
```

The installable plugin ZIP is written to:

```text
build/distributions/intellij-aidl-plugin-0.1.0-SNAPSHOT.zip
```

Gradle writes to `~/.gradle` and `.intellijPlatform/`; in restricted environments this may require elevated filesystem/network permission.

## Architecture

- `de.kreisgeist.aidl.AidlLanguage` registers the language.
- `de.kreisgeist.aidl.AidlFileType` registers `.aidl`.
- `de.kreisgeist.aidl.lexer.AidlLexer` is handwritten and drives syntax highlighting.
- `de.kreisgeist.aidl.parser.AidlParser` is permissive and creates enough PSI structure for editor features.
- `de.kreisgeist.aidl.psi.AidlTypes` and `AidlTokenSets` define token and element types.
- `de.kreisgeist.aidl.highlighting` contains syntax highlighting and color settings.
- `de.kreisgeist.aidl.references` contains navigation/reference resolution.

The grammar files in `src/main/resources/grammar/` are currently reference resources, not generated sources.

## Language Rules

AIDL has contextual keywords. Do not turn every grammar word into a global lexer keyword.

Current intent:

- Top-level declaration starters are keywords only outside braces.
- `module`, `import`, and `export` are declaration-level keywords.
- Scalar types and expression literals/operators such as `string`, `int`, `true`, `false`, `null`, `and`, `or`, `not`, `in`, and `ref` are lexed as keywords.
- Forced syntax words such as declaration-level `version` clauses are keywords where the grammar requires them.
- Profile and clause names such as `profile`, `system`, `frontend`, `api`, `cache`, `auth`, `route`, etc. are `PROPERTY_NAME` inside blocks and are highlighted like named parameters.
- Any identifier after `.` must remain an identifier/type name, not a keyword. Example: `import videohub.ui.app.VideoHubWeb`.

When adding new words, decide whether they are:

- a true keyword,
- a forced grammar connector,
- a scalar/expression keyword,
- a contextual property name,
- or just an identifier.

## Navigation

Reference resolution is intentionally lightweight:

- Module declarations are parsed as `MODULE_NAME`.
- Import paths are parsed as `IMPORT_PATH`.
- Declaration names are parsed as `DECLARATION_NAME` and exposed as named PSI elements.
- References resolve against local declarations, exact imports, and wildcard imports.
- Lowercase operation names such as `listMyEvents` must remain resolvable.

Use the calendar example when changing navigation because it covers:

- exact imports,
- wildcard imports,
- uppercase type declarations,
- lowercase operation declarations.

## Tests

Keep lexer behavior covered in `src/test/kotlin/de/kreisgeist/aidl/lexer/AidlLexerTest.kt`.

At minimum, preserve tests for:

- keywords inside qualified import paths staying identifiers,
- declaration-level `version` handling where still defined by AIDL,
- app-block properties as `PROPERTY_NAME`.

Run `./gradlew check` after changes.
