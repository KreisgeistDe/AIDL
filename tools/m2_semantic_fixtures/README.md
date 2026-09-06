# M2 Semantic Fixture Corpus

This directory is the task-specific M2-13 semantic regression corpus.

It intentionally is **not** the M5 `fixtures/valid/` / `fixtures/invalid/` golden-fixture suite and does not introduce snapshots, canonical IR expectations, plans, generated output, CLI behavior, or IDE behavior.

`manifest.json` lists one isolated negative fixture project for every M2-01 through M2-11 semantic rule. `tools/test_m2_semantic_fixtures.py` loads each project through the existing compiler diagnostic boundary and verifies the complete expected diagnostic code/anchor sequence plus deterministic output under reversed source input order.

Positive counterexamples remain covered by the existing rule-focused M2 tests. M2-13 adds no duplicate positive fixtures because every M2-01 through M2-11 rule already has an explicit valid counterpart test in the existing suite.
