# M10.1 Auth Evidence and Target Contract

This slice keeps auth evidence compiler-owned and diagnostic-neutral and adds the narrow semantic target contract required before a legacy `qualifiedName` auth mode can ever be considered complete. It does **not** yet admit `auth` into the complete M10.1 production semantic set; `spec/language-surface-v1.json` and the production normalization envelope remain unchanged.

The accepted legacy grammar remains `auth: public | authenticated | service | qualifiedName`. `tools/compiler_auth_evidence.py` consumes parser-preserved clause text through existing typecheck `_clauses` and uses existing compiler `_resolve` symbol/import lookup. It introduces no second auth grammar, qualified-name parser, resolver, or diagnostic rule.

For each query/mutation auth clause the evidence records parser-stable `source`, `mode`, resolver `resolution`, unique `target`/`target_kind` when available, explicit `target_status`, the target-contract identity and stable signature facts. Built-ins `public`, `authenticated`, and `service` remain complete directly from the grammar.

The qualified-name target contract is `policy-bool-no-parameters/v1`. A qualified auth name is eligible only when existing compiler resolution yields exactly one target and that target is a non-generic, parameterless `policy` whose declared result is `bool`. This is the narrowest existing named declaration shape that can represent a closed authorization predicate without inventing arguments, implicit data flow, or a new declaration kind. The contract is evaluated only from parser/compiler-owned declaration facts.

All other states fail closed and remain incomplete:

- no resolver match -> `unresolved`;
- more than one match -> `ambiguous`;
- one non-`policy` declaration -> `wrong_kind`;
- a unique policy with parameters, a non-`bool` result, or generic type parameters -> `incomplete`.

The evidence object exposes deterministic semantic serialization and SHA-256 hashing. Equivalent source whitespace yields identical structured evidence and hash, while clause order remains preserved. Evidence extraction and hashing emit no diagnostics and do not mutate existing compiler diagnostics.

Production parity is intentionally unchanged in this package. The frozen language-surface contract still omits `auth` from query/mutation body slots, so operations containing auth remain outside lossless production normalization. A follow-up production-parity package may add contract-owned auth body slots only if it can encode the eligible built-ins and qualified-policy target evidence losslessly while keeping every unresolved, ambiguous, wrong-kind, incomplete, duplicate, or otherwise unsupported auth shape excluded.

Parser acceptance, existing diagnostics, global resolver/typecheck semantics, CLI JSON, Canonical IR, Kotlin/M10.5-03, M16.5 syntax, project `.ai/**`, and unrelated mini-languages remain unchanged.
