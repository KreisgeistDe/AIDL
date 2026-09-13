# M10.3 closure certification

M10.3-01 closes the pre-Kotlin reference-example migration gate without changing the frozen M10.1 language contract, Production Normalization admission, Canonical IR meaning, parser/compiler/runtime semantics, or `app.links` admission.

## Certified inputs

The executable authority is `spec/m10-3-closure-certification.json`, validated by `tools/m10_3_closure_certification.py`. It composes:

- frozen `spec/language-surface-v1.json` revision 4;
- the exhaustive M10.2 source/document classification in `spec/m10-2-language-surface-classification.json`;
- the shared M10.3 disposition in `spec/m10-3-shared-disposition.json`;
- the integrated Calendar, Petstore, and VideoHub source trees and their app-local inventories; and
- the committed valid/compatibility, invalid/rejection, and semantic-diagnostic fixture classes.

The certifier first reruns the complete M10.2 classification. Every committed `.aidl` source must still match exactly one classification rule, every required/discovered AIDL or EBNF documentation surface must remain classified, and the frozen revision-4 identity must still match.

## Reference applications

The three integrated reference applications remain product/reference stories whose production evidence is deliberately narrower than their complete specified syntax surface.

- Calendar: 13 committed `.aidl` sources, inventoried in `examples/calendar-offline/README.md`.
- Petstore: 19 committed `.aidl` sources, inventoried in `examples/petstore/M10.3.md`.
- VideoHub: 25 committed `.aidl` sources, inventoried in `examples/videohub/README.md`.

The certifier compares each live source tree with its inventory. A newly added application source that is not explicitly inventoried fails closed. The already-integrated migrations use only the three shared `supported-equivalent-source-form` classes: app profile blocks, explicit entity `field` slots, and named operation `parameters` header arguments.

## Remaining mismatches

Every shared M10.2/M10.3 mismatch has exactly one durable disposition. `app.links` remains `requires-versioned-admission`; it is not production evidence under revision 4. All other shared mismatch classes remain `non-production-fail-closed`, including currently excluded operation clauses and frozen-but-not-admitted declaration families. The certifier pins the complete ID-to-disposition map and rejects additions, removals, duplicate IDs, or reclassification.

This means closure is not a claim that all syntax demonstrated by the three applications is production-admitted. It certifies that every demonstrated surface is either migrated through an already-admitted equivalent source form or explicitly retained outside Production Normalization. No separately versioned language/admission change was required for M10.3.

## Fixtures and negative evidence

Committed fixture classes remain intentional evidence rather than migration targets:

- `fixtures/valid/**` remains `legacy-readable-compatibility` evidence;
- `fixtures/invalid/**` remains `negative-rejection-fixture` evidence; and
- `tools/m2_semantic_fixtures/**` remains semantic diagnostic/rejection evidence.

The M10.2 classifier continues to own exhaustive source coverage, while the M10.3 certifier verifies that these fixture roots are non-empty and retain their expected classes. Newly inconsistent or unclassified source/document surfaces therefore fail closed.

## Closure result

M10.3-01 is complete when the closure certifier succeeds together with the repository's normal required CI. The resulting Python reference baseline remains revision 4 with unchanged production admission and unchanged Canonical IR meaning. Only after this integrated M10.3 state may M10.5-01 be refreshed/rebased and fingerprinted as the final parity baseline; no Kotlin semantic implementation is started by this closure.
