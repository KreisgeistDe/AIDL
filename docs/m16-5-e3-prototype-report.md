# M16.5 E3 — bounded parser/schema-combinator prototype

Status: **experimental evidence only**. Base: `d853386d00f29ee502fa02c9135e725e98ed08f7` (`main`). This package does not touch the production lexer/parser, AST/IR authority, `docs/06-grammar.md`, accepted syntax, formatter, IDE/LSP, or runtime. The fixture notation is E3-only and does not adopt candidate syntax.

## Prototype boundary

`tools/m16_5_e3_prototype.py` is isolated from production parser/IR imports. Its manually trusted catalog exercises all accepted E1 combinators: whole-node alternatives, ordered slots, named keyed children with `one`/`optional`/`many` cardinality, typed values, and contextual terminals. Catalog identity is `urn:aidl:schema:language:m16.5-e3-candidate`, version `m16.5-e3-candidate-v1`, with a deterministic content fingerprint and process-local single materialization (`lru_cache(maxsize=1)`); schema filesystem loads are zero.

Construction requires explicit matching source/schema versions. Mismatch fails closed as `AIDL-S008`. Known legacy forms fail as `AIDL-S007`; there is no fallback or syntax sniffing. `uiStatement` and `testStatement` are catalogued only as disabled E3 construction surfaces and fail as `AIDL-S005`.

`LosslessSidecar` stores the immutable original source, source/schema fingerprints, token/trivia lexemes with source ranges, and structural anchors. Semantic nodes carry no trivia.

## Matrix coverage

All nine normalization rows have executable fixtures:

| E1 row | E3 explicit shape |
| --- | --- |
| projection relationship | `source`, `target` |
| client target | `service` |
| migration source/target | `from`, `to` |
| consumer relationship | `topic`, `source` |
| keywordless entity/value field | `field <name>: <type>` |
| positional index tuple | `fields`, optional `unique` |
| queue deadLetter tuple | `queue`, `deadletter` |
| schedule lease compound | `schedule`, `lease` |
| sync changes/outbox | `changes`, `outbox` |

Representative existing families are `app`, `service`, `api`, `event`, `workflow`, and `deployment`. Ordered workflow `step` values exercise sequence preservation; repeated field/resource/route/step entries exercise `many` cardinality. The notation abstracts production punctuation/subgrammars and therefore demonstrates metamodel fit, not production-parser parity.

## Structural diagnostics

The bounded constructor uses only E2 `AIDL-S###` codes for schema-owned failures: `S001` missing, `S002` duplicate singleton, `S003` unknown item/kind, `S004` wrong value/cardinality/alternative, `S005` invalid local structure or explicit E3 exclusion, `S007` legacy spelling rejected by target context, and `S008` source/schema mismatch. Semantic diagnostics are outside this prototype.

## Executed validation

```text
python3 -m compileall -q tools/m16_5_e3_prototype.py tools/test_m16_5_e3_prototype.py
# exit 0

python3 -m unittest -v tools.test_m16_5_e3_prototype
# 10 tests, OK
```

The tests cover all nine normalization rows, six representative families, byte-exact reconstruction of comments/whitespace/literal lexemes, anchors, process-cache reuse, stale and independently mismatched versions, legacy rejection/no fallback, `uiStatement`/`testStatement` exclusion, `AIDL-S001/2/3/4/5/7/8`, and semantic stability under trivia-only changes.

Repository-wide production regressions are left to the existing PR `python-validation.yml` because E3 intentionally does not fork the production parser/IR. That workflow runs required compiler/CLI regressions, all generic Python tests, spec lint, Petstore parser smoke, compatibility policy, golden fixtures, and other project checks; remote CI status is recorded with the PR/result evidence.

## Controlled startup benchmark

Command: `python3 -m tools.m16_5_e3_prototype --benchmark`.

Captured machine class: Linux 6.18.35 x86_64, 5 visible CPUs, Python 3.13.5. Protocol: **10 cold fresh-process runs**, then **5 warmups + 30 measured warm runs in one process**. No threshold is applied. Catalog cache after the warm protocol: 1 miss, 69 hits, size 1; schema filesystem loads: 0.

Cold raw ns:
`[747569, 802048, 850346, 807973, 1530114, 1289758, 778963, 744663, 781604, 735492]`

Cold summary ns: min `735492`; median `791826.0`; mean `906853.0`; max `1530114`; pstdev `259250.77469469595`.

Warm raw ns:
`[52345, 72422, 54671, 51085, 50325, 67124, 54250, 69937, 54100, 52268, 68389, 53368, 51231, 81797, 59013, 51216, 50470, 49755, 50159, 50794, 49977, 50270, 49525, 50035, 49037, 59150, 60719, 50602, 49311, 48654]`

Warm summary ns: min `48654`; median `51223.5`; mean `55399.96666666667`; max `81797`; pstdev `8237.105885294637`.

Raw values are authoritative only for this bounded workload/machine and are not a production latency claim.

## Special-case deltas / risks

The common model fits the bounded matrix, but E3 does not establish full production equivalence. Recursive selection/property trees are only represented by the combinator vocabulary, not exhaustively parsed. Ordered control/effect blocks are represented by ordered workflow steps, not all nested branch semantics. Contextual-terminal conflicts across the full grammar were not measured. The sidecar proves losslessness for bounded parses but not edit reattachment, overlapping plans, or incremental reparses. `uiStatement`/`testStatement` remain deliberate FreeItem exceptions. Candidate spelling still requires the E2 migration/fingerprint/anchor/idempotence/M7 gates before any language change.

## Recommendation

**Proceed to E4 only as a gated extension, not a production-parser replacement.** E4 should require full declaration-corpus parity, deep recursive selection/property and ordered control-flow coverage, unchanged-invalid recovery/diagnostic parity, sidecar edit/anchor stress tests, and M7 semantic equivalence for any candidate rewrite. If those fail, revise the combinator model rather than add compatibility fallbacks.
