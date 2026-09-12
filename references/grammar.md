# Grammar Reference

## Authority

This reference is a compact navigation aid for the frozen M10.1 revision-4 target language. The machine-readable authority is `spec/language-surface-v1.json`; the normative human-readable projection is `docs/06-grammar.md`. This page must not define an independent grammar.

Canonical target syntax, parser-readable compatibility syntax, and current production admission are distinct. Current production support is determined by the M10.1 Production Semantic Envelope certification, not by the presence of a declaration kind on this page.

## Uniform declaration shape

```ebnf
program         = { directive | declaration } ;
directive       = moduleDirective | importDirective ;
declaration     = { annotation } [ "export" ] kind [ name ]
                  [ headerArguments ] [ "->" typeRef ]
                  "{" { bodySlot } "}" ;
headerArguments = "(" [ namedArgument { "," namedArgument } ] ")" ;
namedArgument   = identifier ":" value ;
```

The exact name policy, header arguments, result-type allowance, body slots, cardinalities, reference kinds and legacy forms are contract-owned.

## Canonical revision-4 declaration kinds

`app`, `auth`, `a11y`, `privacy`, `enum`, `alias`, `value`, `union`, `error`, `entity`, `view`, `api`, `policy`, `query`, `mutation`, `event`, `topic`, `queue`, `consumer`, `projection`, `workflow`, `saga`, `task`, `schedule`, `system`, `service`, `client`, `tenant`, `channel`, `resource`, `media`, `rendition`, `sync`, `migration`, `deployment`, `frontend`, `theme`, `component`, `page`, `form`, `action`, `syncStatus`, `seo`, `nativeFunction`, `nativeComponent`, `fixture`, `test`, and `scenario`.

Only the separately certified M10.1 production-admitted subset is executable production evidence today; other canonical families remain fail-closed.

## Compatibility-only source forms

The parser may still read historical forms required for compatibility and migration. They are non-canonical and must not be used as target-language grammar rules. Important examples include:

- bare comma-separated enum cases instead of explicit `case` slots;
- `opaque Name = Type` instead of canonical `alias`;
- unprefixed entity members instead of explicit `field` slots;
- positional operation, consumer, projection, client and migration headers instead of contract-owned named arguments;
- parser-readable clauses or declaration families that current Production Normalization rejects.

M10.2 classifies those surfaces; M10.3 owns executable migration/disposition of intended reference examples.

## Repository classification

`spec/m10-2-language-surface-classification.json` records support tiers for committed AIDL sources and syntax/semantic documentation. `python3 -m tools.m10_2_language_surface_classification` fails closed on new unclassified or multiply classified source, unclassified AIDL/EBNF documentation, manifest drift, and frozen-contract identity drift.
