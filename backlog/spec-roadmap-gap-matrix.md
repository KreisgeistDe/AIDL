# Specification-to-roadmap gap matrix

This matrix compares specified language/product surfaces with the durable roadmap. It is planning evidence only. Specification text means **specified**, not implemented or supported. Current implementation/support authority remains `spec/conformance-manifest.json` plus the applicable detailed conformance/evidence contracts.

| Spec surface | Representative specified facts | Existing roadmap coverage before M17+ | Gap | Planned owner | Claim boundary |
|---|---|---|---|---|---|
| `docs/01-core-language.md` — extended scalar/type system | constrained strings/numbers, `date`, `duration`, `email`, `url`, `bytes`, `json<S>`, list/set/map/nullability composition, dimensions | M1–M3 established bounded Core compiler/IR; M10 closes current Core claims | broad specified type surface lacks an explicit post-Core implementation milestone | **M17** | no support promotion until conformance evidence exists |
| `docs/01-core-language.md` — generics | generic value/union/view/component/native function, bounds, invariance, monomorphization, expansion diagnostics | no existing milestone owns complete generic language semantics | missing language/compiler/IR plan | **M17** | generic syntax remains specified until implemented and evidenced |
| `docs/01-core-language.md` — unions/views/alias/opaque/value details | discriminated unions, generic views, wire representation, nominal opacity, field presence/mutability | M10 has focused Core evidence but intentionally partial declaration cells remain | no milestone owns exhaustive extended declaration closure after M10 | **M17**, then **M21** | focused evidence must not be read as whole-cell/full-language support |
| `docs/11-standard-library.md` — stdlib/versioning | identity/time types, paging, standard errors, Result/AsyncState, idempotency, media/sync/realtime/UI values, units | current Core has selected built-ins; no roadmap milestone owns complete independently versioned `aidl.std` | missing stdlib implementation/version-resolution plan | **M17** | stdlib documentation does not imply packaged/compiler availability |
| `docs/02-backend.md` — API/query/mutation | REST/RPC/GraphQL, rate limits, consistency/cache, idempotency, remote auth, root effects | M2/M4 cover selected semantics and one REST runtime slice | specified backend clauses exceed explicit compiler/IR roadmap | **M18** | M18 language completion does not imply general runtime support |
| `docs/02-backend.md` — transaction/policy/event/consumer | isolation, CAS flow typing, locks, outbox, policies, events/topics, consumers | M2/M10 have selected semantic and IR evidence; M12 owns runtime | remaining language/IR surface lacks cohesive owner | **M18** for language; **M12** for runtime | runtime claims require M12 evidence |
| `docs/02-backend.md` — projection/workflow/saga/task/schedule/native | replay/rebuild, compensation, approvals/timeouts, worker budgets, scheduler leases, capability-limited native functions | M12 plans runtime pieces, but no complete language/compiler milestone | runtime roadmap would otherwise be forced to define semantics | **M18** for language; **M12–M15** for runtime/provider | adapters may not redefine language semantics |
| `docs/03-frontend.md` — frontend structure | frontend/target/rendering/theme/locale/routes/capabilities/fallbacks | `profile.web` is only `specified`; no frontend language milestone | direct roadmap omission | **M19** | profile.web remains specified/partial until conformance authority changes |
| `docs/03-frontend.md` — typed UI/data/state | components/generics, pages/data consistency, state lifetimes, forms, optimistic/offline actions, sync/realtime | M13/M14 cover runtime scenarios indirectly; no compiler-authoritative UI plan | direct roadmap omission | **M19** | M13/M14 runtime success cannot by itself establish frontend language support |
| `docs/03-frontend.md` — quality/native UI | design tokens, A11y, SEO, privacy, uploads, native component capabilities/SSR/offline | no dedicated roadmap owner | direct roadmap omission | **M19** | target adapter evidence required for Generate claims |
| `docs/07-distributed-systems.md` | system/service/reliability, ownership, clients, delivery/order, consistency, projections, sagas, channels, tenants, identities | M12 owns distributed runtime; current profile is partial | language/compiler/IR coverage is mixed into runtime intent and incomplete | **M20** language; **M12** runtime | M20 cannot claim multi-service runtime |
| `docs/08-offline-sync.md` | sync modes, operation log, clocks, merges, tombstones, rejection, attachments, schema migration | M13 owns offline runtime; profile is partial | explicit complete language/IR milestone missing | **M20** language; **M13** runtime | no sync-engine claim from M20 alone |
| `docs/09-resources-deployment.md` | portable resources, media resources, deployments, regions/failover, serverless, secrets/config, observability/provider capabilities | M14 runtime/provider slice and M15 adapter ecosystem | resource/deployment language semantics are not independently planned | **M20** language; **M14–M15** provider/runtime | provider support needs adapter capability/conformance evidence |
| `docs/10-evolution-compatibility.md` | independent versions, API/event/schema/sync/rolling/deprecation evolution | M7 implements a compatibility authority with a different current classification vocabulary | spec/implementation terminology and remaining evolution-language constructs need explicit reconciliation | **M20**, using **M7** as authority | no second compatibility classifier; mapping must be versioned/tested |
| Cross-profile composition | frontend+offline, distributed+resources, media+cloud, API+evolution, tenant propagation | reference fixtures and M12–M15 exercise selected paths | no exhaustive conformance owner across profiles/layers | **M21** | only evidence-backed composed surfaces may be claimed supported |
| Full-language support claims | complete Parse/Resolve/Validate/IR/Generate/IDE/runtime evidence as applicable | M10 is Core-specific; `spec/conformance-manifest.json` has repository-level statuses | no full-language/profile conformance closure milestone | **M21** | roadmap and specification never supersede conformance authority |

## Responsibility boundaries

- **M10** remains the Core conformance foundation; its existing completion state is unchanged.
- **M11** remains compiler-service/editor-neutral infrastructure; M17–M21 consume it but do not redefine its lifecycle/cache work.
- **M12** remains the distributed runtime vertical slice.
- **M13** remains the offline Calendar runtime vertical slice.
- **M14** remains media/cloud/realtime runtime plus bounded provider work.
- **M15** remains adapter ecosystem, migration/security/operational evidence, and 1.0 readiness.
- **M16** remains agent construction and verification.
- **M17–M20** add missing language/compiler/Canonical-IR planning only.
- **M21** generalizes the M10 evidence discipline to the full set of surfaces the project elects to support.

## Priority rationale

1. **M17** first, because backend/frontend/profile surfaces depend on a coherent extended type system and independently versioned stdlib.
2. **M18** next, because backend contracts are dependencies for distributed runtime, frontend data/mutations, and many compatibility facts.
3. **M19** follows once referenced operation/type contracts are compiler-authoritative.
4. **M20** closes architecture-heavy language contracts while keeping their runtime/provider execution in M12–M15.
5. **M21** comes last because exhaustive conformance is meaningful only after the intended supported language surface is implemented and applicable runtime/generator/editor evidence exists.
