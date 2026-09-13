# Core self-description correction — P3

## Status

P1 is integrated as `755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9`. P2 / PR #101 is independently validated and integrated as `7280f01a2c97b004c79cd0a2e598513bfa183ac0`. This P3 candidate migrates semantic loading, type-carrier resolution and compatibility authorization to the direct self-described Core. P4 and semantics-dependent Kotlin work remain frozen.

## Authority flow

`spec/core-self-description-v1.aidl` is the normative semantic source. It directly defines declaration kinds, name policies, body contracts, modifiers, AIDL-visible type carriers, enum-produced type carriers, the finite runtime behavior metadata for `choice`, `ref` and `expression`, and the `compatibilityProjection` contract.

`tools/core_self_description.py` validates that direct source through the finite Bootstrap Kernel and deterministically derives `spec/core-meta-ir-v1.json`. The derived file declares `authorityInput=false`, carries the exact source SHA-256, and is accepted by `tools/core_semantics.py` only when byte-for-byte regeneration from the direct source matches. It is runtime projection data, not independent authority.

`tools/core_semantics.py` no longer interprets `ArgumentDefinition`, `ModifierDefinition`, `BodySlotDefinition`, `DeclarationDefinition`, `MetaCombinatorDefinition` or `SemanticMetaModel`. Supplying the legacy `spec/core.aidl` / `spec/core-registry-v1.json` pair as semantic inputs fails closed. Declaration-bearing legacy semantic modules fail closed as well.

`spec/core.domain.aidl` and `spec/core.authority.aidl` remain as declaration-free compatibility shells for import/path continuity only. Their former Definition-object declarations are no longer runtime semantic authority. `spec/core-registry-v1.json` remains migration evidence only.

## Runtime semantics

The runtime `SemanticRegistry` is reconstructed from the exact derived meta-IR. Visible TypeRef bases are replaced from the direct AIDL-derived type-carrier set, so `string`, `bool`, `int`, enum instances such as `NamePolicy`, and generic carriers are not selected from the historical host base-type catalog. The runtime engine still implements only finite generic behaviors (`choice`, declaration-reference-kind and expression); those behavior assignments and arities are carried by AIDL `type` declarations in the direct source.

The representative `entity` contract flows through the same path. Its fields accept direct type carriers and `ref<entity>` with existing unresolved/wrong-kind checks, invariants retain expression<bool> validation, and `primary` / `unique` modifier contracts are derived from the direct body contract. No `entity`- or `enum`-specific host dispatch is introduced.

## Compatibility boundary

`tools/core_authority.py` now validates `spec/core.compatibility.aidl` with the direct Core-derived registry. Revision 4 remains frozen compatibility/migration evidence and still requires the exact Core-authored source, blob SHA-1 and `compatibility-only` role binding before production normalization may consume it.

## Deferred work

P3 does not perform P4 downstream surface migration, Kotlin semantic parity, Canonical IR redesign, Production Normalization widening, or public support expansion. PR #99 and M10.5-03+ remain frozen until this P3 candidate is independently validated and integrated.
