# Core self-description — P3 history and semantic correction

## Status

P1 is integrated as `755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9`. P2 / PR #101 is integrated as `7280f01a2c97b004c79cd0a2e598513bfa183ac0`. P3 / PR #102 exact implementation head `4992c896cf9818ab51c6ade60fd2a58c657461fe` was independently validated and squash-integrated as `ca87cdc2ef0ce6e00808512897144ea99ef59293`. PR #103 then reconciled that durable status on `main` as `bb8fb6ff9eb18429c94e9982a9e8d3e03a7ef48d`.

A later architecture review found two P1–P3 semantic interpretations incorrect: `produces(type)` must not define declaration-instance type-carrier capability, and `type-position` is not an irreducible host marker. This correction supersedes those interpretations while retaining direct AIDL self-description as the normative authority. P4, PR #99, M10.5-03+ and all semantics-dependent downstream/Kotlin feature work remain frozen until this correction is independently validated and integrated.

## Corrected declaration envelope

The finite Bootstrap Kernel owns only declaration framing. Args presence and the existing `->` result position are fundamental parts of the envelope. Direct Core declaration-kind contracts restrict that envelope:

- no args contract means Args=`void`/not-present and an explicit argument list fails closed;
- an args contract makes the slot available, including a distinct present-empty list;
- no `->` contract means Return=`void`/not-present and an instance arrow fails closed;
- a direct `-> <return-contract>` is the only result mechanism. There is no parallel `produces` capability.

The base self-description therefore carries the general args/result envelope, while kinds such as `enum` omit both and a kind such as `query` may author both.

## TypeRef identity

A TypeRef is admitted by generic visible named-declaration symbol identity. `type string`, `type bool`, `type int`, enum instances such as `NamePolicy`, and user declarations such as `enum MyEnum` are resolved by the same symbol rule. No concrete declaration-kind table and no `produces(<carrier-space>)` mechanism participates in TypeRef identity.

The direct Core authors position-specific contracts. Entity fields are type-valued because the `entity` declaration-kind contract says so; the host does not special-case `entity`, `enum`, `query`, or `type`. Unresolved or ambiguous named TypeRefs fail closed.

## Authority flow

`spec/core-self-description-v1.aidl` remains the normative semantic source. `tools/core_self_description.py` validates that source through the finite Bootstrap Kernel and deterministically derives `spec/core-meta-ir-v1.json`. The derived file declares `authorityInput=false`, carries the exact source SHA-256, and is accepted by `tools/core_semantics.py` only when byte-for-byte regeneration matches. It is runtime projection data, never independent authority.

`spec/core.domain.aidl` and `spec/core.authority.aidl` remain declaration-free compatibility shells. `spec/core-registry-v1.json` remains historical migration/conformance evidence only. Revision 4 remains frozen compatibility/migration evidence and production use still requires the exact Core-authored compatibility binding.

## Deferred work

This correction does not authorize P4 downstream surface migration, Kotlin semantic parity, Canonical IR redesign, Production Normalization widening, or public support expansion. PR #99 and M10.5-03+ remain frozen pending explicit post-integration authorization.
