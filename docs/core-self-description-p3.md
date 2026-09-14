# Core self-description — P3 history and binding EBNF correction

## Status

P1 is integrated as `755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9`. P2 / PR #101 is integrated as `7280f01a2c97b004c79cd0a2e598513bfa183ac0`. P3 / PR #102 exact implementation head `4992c896cf9818ab51c6ade60fd2a58c657461fe` was independently validated and squash-integrated as `ca87cdc2ef0ce6e00808512897144ea99ef59293`. PR #103 then reconciled that durable status on `main` as `bb8fb6ff9eb18429c94e9982a9e8d3e03a7ef48d`.

Later critical architecture work superseded several P1–P3 interpretations. `produces(type)` is not a declaration-instance carrier capability, `type-position` is not an irreducible host marker, and `type` is not a second fundamental declaration hierarchy. The binding EBNF correction keeps direct AIDL self-description normative while making `declaration` the single self-referential meta-class and `type` a direct syntax/semantic alias of that same category. P4, PR #99, M10.5-03+ and all semantics-dependent downstream/Kotlin feature work remain frozen until this correction is independently architecturally reviewed, exact-head validated, and integrated.

## Central declaration/type model

`declaration` is both the central meta-class and itself a type object. Every visible named AIDL declaration is therefore TypeRef-addressable by symbol identity. This includes declaration-kind definitions such as `entity`, concrete declarations such as `entity User`, enums, and named queries. `type string`, `type bool`, and `type int` are alias spellings through the direct-Core-authored `type -> declaration` mapping; they do not create a parallel type-class world.

The derived meta-IR records one canonical `declaration` contract plus `kindAliases: {"type": "declaration"}`. That normalized representation is output-only and does not become language authority.

## Binding declaration envelope

The finite Bootstrap Kernel owns syntax/framing while direct Core contracts supply semantic meaning. Every declaration uses one envelope:

`[export] type-reference identifier [generic-parameters] [named-arguments] [-> type-reference] [declaration-body] [statement-end]`

There is no dedicated `type` grammar production. The binding argument and result rules are:

- omitting `(...)` means a closed contract with exactly zero parameters;
- explicit empty declaration parentheses `()` are invalid syntax and fail closed;
- explicit named arguments form a closed fixed parameter set and use TypeRefs, optional `?`, and optional defaults;
- an open parameter set uses a free binder such as `(args?: ...)` or `(params?: ...)`; the spelling is not semantically fixed;
- a non-empty signature fails closed for a specialized kind whose direct contract has no open argument specification;
- no return specification on a specialized kind forbids an instance arrow;
- a specialized direct `-> <return-contract>` requires and validates that result TypeRef;
- the self-referential base `declaration ... -> any` is the maximally general envelope and does not force every declaration-kind definition or ordinary declaration spelling to carry an arrow;
- `->` is the only result mechanism. There is no parallel `produces` capability.

Body entries use `<body-type> [name] [: value] [modifiers...]`. Values are general expressions whose expected semantics come from the enclosing declaration contract. Indentation has no meaning. A newline may continue an incomplete expression/value or a following modifier, while semicolon always terminates and newline terminates only a complete construct.

The syntax boundary also includes recursive generic/nullable TypeRefs, the specified logical/equality/comparison/additive/multiplicative/unary precedence, member/call/index postfix forms, range and list values, nested block comments, normal strings, raw multiline strings with an optional immediate language tag, and interpolation via `$qualified.name`, `${expr}`, and `$$`.

## TypeRef identity

A TypeRef base resolves to one visible named declaration symbol. `entity User`, `enum MyEnum`, a named query such as `myQuery`, declaration-kind names such as `entity`, and alias-spelled declarations such as `type string` all use the same rule. No concrete declaration-kind table and no `produces(<carrier-space>)` mechanism participates in TypeRef identity.

The direct Core authors position-specific contracts. Entity fields are type-valued because the `entity` declaration-kind contract says `body field: body(type, ...)`; the host does not special-case `entity`, `enum`, `query`, or other concrete kinds. Unresolved or ambiguous named TypeRefs fail closed.

## Authority flow

`spec/core-self-description-v1.aidl` remains the normative semantic source. `tools/core_self_description.py` validates that source through the finite Bootstrap Kernel and deterministically derives `spec/core-meta-ir-v1.json`. The derived file declares `authorityInput=false`, carries the exact source SHA-256, and is accepted by `tools/core_semantics.py` only when byte-for-byte regeneration matches. It is runtime projection data, never independent authority.

`spec/core.domain.aidl` and `spec/core.authority.aidl` remain declaration-free compatibility shells. `spec/core-registry-v1.json` remains historical migration/conformance evidence only. Revision 4 remains frozen compatibility/migration evidence and production use still requires the exact Core-authored compatibility binding.

## Deferred work

This correction does not authorize P4 downstream surface migration, Kotlin semantic parity, Canonical IR redesign, Production Normalization widening, or public support expansion. PR #99 and M10.5-03+ remain frozen pending explicit post-integration authorization. The next task is independent architecture review plus exact-head validation of the completed binding EBNF target; the implementation agent must not self-review or merge.
