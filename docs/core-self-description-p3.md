# Core self-description — P3 history and semantic correction

## Status

P1 is integrated as `755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9`. P2 / PR #101 is integrated as `7280f01a2c97b004c79cd0a2e598513bfa183ac0`. P3 / PR #102 exact implementation head `4992c896cf9818ab51c6ade60fd2a58c657461fe` was independently validated and squash-integrated as `ca87cdc2ef0ce6e00808512897144ea99ef59293`. PR #103 then reconciled that durable status on `main` as `bb8fb6ff9eb18429c94e9982a9e8d3e03a7ef48d`.

Later critical architecture work superseded several P1–P3 interpretations. `produces(type)` is not a declaration-instance carrier capability, `type-position` is not an irreducible host marker, and `type` is not a second fundamental declaration hierarchy. The amended correction keeps direct AIDL self-description normative while making `declaration` the single self-referential meta-class and `type` a direct syntax/semantic alias of that same category. P4, PR #99, M10.5-03+ and all semantics-dependent downstream/Kotlin feature work remain frozen until this correction is independently architecturally validated, exact-head validated, and integrated.

## Central declaration/type model

`declaration` is both the central meta-class and itself a type object. Every visible named AIDL declaration is therefore TypeRef-addressable by symbol identity. This includes declaration-kind definitions such as `entity`, concrete declarations such as `entity User`, enums, and named queries. `type string`, `type bool`, and `type int` are alias spellings through the direct-Core-authored `type -> declaration` mapping; they do not create a parallel type-class world.

The derived meta-IR records one canonical `declaration` contract plus `kindAliases: {"type": "declaration"}`. That normalized representation is output-only and does not become language authority.

## Corrected declaration envelope

The finite Bootstrap Kernel owns only declaration framing. The existing argument syntax and `->` result position are structural parts of the envelope; direct Core contracts supply their meaning:

- `args(...)` on a declaration-kind contract denotes an open parameter set;
- an explicit declaration signature is a closed fixed parameter set;
- no args specification and an explicit empty `()` signature are the same closed zero-parameter semantic model;
- a non-empty signature fails closed for a kind whose direct contract has no `args(...)` specification;
- no return specification on a specialized kind forbids an instance arrow;
- a specialized direct `-> <return-contract>` requires and validates that result TypeRef;
- the self-referential base `declaration ... -> any` is the maximally general envelope and does not force every declaration-kind definition or ordinary declaration spelling to carry an arrow;
- `->` is the only result mechanism. There is no parallel `produces` capability.

## TypeRef identity

A TypeRef base resolves to one visible named declaration symbol. `entity User`, `enum MyEnum`, a named query such as `myQuery`, declaration-kind names such as `entity`, and alias-spelled declarations such as `type string` all use the same rule. No concrete declaration-kind table and no `produces(<carrier-space>)` mechanism participates in TypeRef identity.

The direct Core authors position-specific contracts. Entity fields are type-valued because the `entity` declaration-kind contract says `body field: body(type, ...)`; the host does not special-case `entity`, `enum`, `query`, or other concrete kinds. Unresolved or ambiguous named TypeRefs fail closed.

## Authority flow

`spec/core-self-description-v1.aidl` remains the normative semantic source. `tools/core_self_description.py` validates that source through the finite Bootstrap Kernel and deterministically derives `spec/core-meta-ir-v1.json`. The derived file declares `authorityInput=false`, carries the exact source SHA-256, and is accepted by `tools/core_semantics.py` only when byte-for-byte regeneration matches. It is runtime projection data, never independent authority.

`spec/core.domain.aidl` and `spec/core.authority.aidl` remain declaration-free compatibility shells. `spec/core-registry-v1.json` remains historical migration/conformance evidence only. Revision 4 remains frozen compatibility/migration evidence and production use still requires the exact Core-authored compatibility binding.

## Deferred work

This correction does not authorize P4 downstream surface migration, Kotlin semantic parity, Canonical IR redesign, Production Normalization widening, or public support expansion. PR #99 and M10.5-03+ remain frozen pending explicit post-integration authorization.
