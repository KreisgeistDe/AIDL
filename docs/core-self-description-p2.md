# Core self-description correction — P2

## Status and authority boundary

P1 is integrated on `main` as `755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9`. P2 establishes the direct self-description and type-carrier contract without starting the P3 semantic-loader/meta-IR migration or P4 downstream/Kotlin rebase.

`spec/core-self-description-v1.aidl` is the P2 normative direct self-description. Concrete declaration kinds are declared in AIDL through the finite Bootstrap Kernel vocabulary `name`, `args`, `body`, `cardinal`, `modifier`, `type-position`, and `produces`. The host has no table of concrete kinds such as `entity` or `enum`.

The pre-correction `spec/core.aidl` / `spec/core-registry-v1.json` Definition-object path remains only as a temporary runtime compatibility and migration adapter until serialized P3 replaces that loader dependency. It is not the permanent corrected meta-model and must not gain new language semantics. The generated registry remains non-authoritative output.

## Direct declaration-kind contracts

P2 defines `declaration`, `type`, `enum`, and `entity` directly in AIDL. `declaration` is recursively self-described: its body admits named `body(...)` entries, so new declaration kinds can be introduced by source definitions without adding host/compiler branches.

`type` is itself a declaration kind. Visible names including `string`, `bool`, and `int` are declared as `type` instances in AIDL; they are not a host-owned base-type catalog.

`enum` uses the same general carrier rule as `type`: any declaration-kind contract containing `produces(type)` makes each named instance of that kind a valid type carrier. `NamePolicy` and `CardinalityLabel` demonstrate enum instances in that carrier space. There is no enum-specific host rule.

`entity` is directly declared with `field` and `invariant` body contracts. `CoreEntityExample` proves that a concrete `entity` instance can use `string` and the enum instance `NamePolicy` at type positions without the host knowing the concrete declaration kind.

## Deterministic fail-closed behavior

`tools/core_self_description.py` compiles the direct source using only P1 parsing and structural meta-combinators. It fails closed on undefined declaration kinds, malformed or duplicate structural contracts, cardinality violations, undeclared modifiers, duplicate named body bindings, and unresolved type carriers. Recursive generic type arguments use the same carrier rule.

The type-carrier rule is machine-readable in `spec/bootstrap-kernel-v1.json`; `hostKnowsConcreteProducerKinds` is false. `spec/core-authority-transition-v1.json` records P2 evidence, the temporary legacy adapter role, and P3 as the next serialized implementation phase after independent P2 validation/integration.

## Deferred work

P2 does not migrate `tools/core_semantics.py`, `spec/core.domain.aidl`, compatibility normalization, Canonical IR, production admission, CLI/IDE semantics, or Kotlin semantic implementations to the direct model. Those are P3/P4 responsibilities. PR #99 and M10.5-03+ remain frozen while the authority correction is incomplete.
