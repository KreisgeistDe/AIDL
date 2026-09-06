# Frontend

## Boundary

The frontend layer describes UI semantics, data flow, local persistence, and quality requirements. It is not a JSX/CSS replacement. Generators may target web, mobile, or desktop as long as they preserve the contract.

## Frontend and Routes

```dsl
frontend PetstoreWeb {
  target web
  rendering hybrid
  theme PetTheme
  locale default "de-DE" supported ["de-DE", "en-US"]
  route "/" -> PetCatalog
  route "/pets/:petId/adopt" -> AdoptionPage auth authenticated
  fallback -> NotFoundPage
}
```

Targets: `web`, `mobile`, `desktop`. Platform capabilities must be declared with fallbacks; pages cannot assume platform-specific features silently.

## Theme

Themes declare tokens for color, spacing, radius, typography, and contrast. Components may use only declared tokens. Free values need `visualOverride` with a reason. Generators must validate contrast and scaling for target platforms.

## Components

Components are pure. They cannot directly write persistence, topics, or arbitrary network endpoints. Generic components are type-checked per concrete instantiation.

Use semantic UI statements such as `semantic`, `layout`, `image`, `heading`, `button`, `list`, `grid`, `repeat`, and `render`; valid names are closed by the web profile schema.

## Pages and Async Data

Pages can declare route state, data sources, async states, and `main`.

State kinds:

- `urlState`: URL/browser history.
- `data`: query cache, volatile or profile-dependent.
- `form`: until submit/reset.
- `state`: component instance.
- `sessionState`: secure session store.
- `localState`: declared local store.
- `replicatedState`: sync engine state.

Every async source needs `loading`, `empty`, and `error` unless statically impossible. Eventual sources also need stale/refreshing behavior.

## Forms and Mutations

Forms bind typed input, validation timing, submit mutation, and outcome handling.

Idempotency IDs must survive network retries. A generator must not reevaluate `uuid()` for each retry. Failure clauses may target specific errors before a generic failure clause.

## Optimistic and Offline Actions

Connected optimistic action assumes a reachable server and rolls back on failure.

Offline action writes to the operation log and is not rolled back on network failure. It must display pending, conflict, and rejected states according to the sync contract.

Destructive actions need confirmation or undo. Offline delete must surface tombstone semantics when the sync contract can produce them.

## Sync Status

Offline frontends declare global and entity sync status UI. If the sync contract can produce `rejected` or `manualConflict`, the UI must handle them.

When a query uses an offline sync source, the generator reads confirmed local state first, overlays pending operations, then synchronizes. Pending, conflict, and rejected remain separate states.

## Realtime and Uploads

Realtime data sources need reconnect, resume, or full reload fallback. UI cannot assume stronger delivery or ordering than the channel contract.

Uploads declare mode, accepted media, max size, progress/paused/completed/rejected states. Local file paths and raw bytes must not enter logs, telemetry, or query cache. Upload tokens are short-lived sensitive handles.

## A11y, SEO, Privacy

A11y can require WCAG 2.2 AA, keyboard support, visible focus, reduced motion, and image alt text.

SEO attaches typed title/description/canonical declarations to pages.

Privacy rules include analytics consent and data handling. Sensitive data must persist only in stores with matching encryption/deletion contracts.

