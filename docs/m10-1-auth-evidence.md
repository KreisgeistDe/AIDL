# M10.1 Auth Evidence Prerequisite

This slice adds compiler-owned, diagnostic-neutral evidence for legacy query/mutation `auth` clauses. It is intentionally a prerequisite only: `auth` is **not** admitted into the complete M10.1 production semantic set, `spec/language-surface-v1.json` is unchanged, and the production normalization envelope remains unchanged.

The accepted legacy grammar remains `auth: public | authenticated | service | qualifiedName`. `tools/compiler_auth_evidence.py` consumes the parser-preserved generic clause text through the existing typecheck `_clauses` projection and uses the existing compiler `_resolve` symbol/import lookup. It introduces no second auth grammar, text splitter, qualified-name parser, resolver, or diagnostic rule.

For each query/mutation auth clause the evidence records:

- `source`: parser-preserved token identity, stable across source whitespace;
- `mode`: `builtin` or `qualified_name`;
- `resolution`: `builtin`, `resolved`, `unresolved`, or `ambiguous`;
- `target` and `target_kind` only for a unique existing compiler resolution;
- `complete`: true only for the grammar-defined built-ins `public`, `authenticated`, and `service`.

Qualified names deliberately remain incomplete even when the existing symbol table resolves them uniquely. The current compiler has no semantically authorized declaration kind that a qualified auth name is defined to target. A uniquely resolved `value`, `service`, `auth`-adjacent declaration, or any other named declaration therefore supplies lookup evidence only; it does not acquire auth semantics. Unresolved and ambiguous names are likewise incomplete. A future production-parity slice must first freeze an explicit auth target contract backed by existing compiler facts or add that prerequisite in its own authorized language-design change.

The evidence API emits no diagnostics and does not change existing parser acceptance, compiler diagnostics, global resolver/typecheck behavior, CLI JSON, Canonical IR, Kotlin/M10.5-03, or M16.5 syntax. Cache, idempotency, consistency, authorize, transaction, and other pending mini-languages remain out of scope.
