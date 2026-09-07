# M9-08 scoped toolchain pre-release workflow

M9-08 promotes the deterministic M9-05 bundle into the first explicitly scoped public toolchain pre-release. It does not create or move tags from pull requests, does not claim native `main` protection is enforced, and does not widen language-profile support.

## Version, tag, and publication contract

`release/release.json` remains the release control record. Schema version 1 now requires:

- distribution `aidl-toolchain`;
- PEP 440 pre-release version `0.1.0rc1`, matching `[project].version` in `pyproject.toml`;
- exact tag `aidl-toolchain-v0.1.0rc1` (`<distribution>-v<version>`);
- `CHANGELOG.md` as the committed notes authority;
- tracked root `spec/*.json` files as the contract inventory;
- publication state `github-prerelease-on-tag`.

A non-pre-release package version, mismatched package version, mismatched configured tag, or mismatched actual tag fails contract validation. Pull requests and manual workflow runs can build and validate but cannot publish.

## Scoped release notes

The current notes section is headed exactly `## 0.1.0rc1 — scoped toolchain pre-release`. `tools.release_bundle` extracts only that section, ending before the next level-two changelog heading. Historical changelog sections therefore cannot silently broaden the public release notes.

The notes promise only surfaces whose `spec/conformance-manifest.json` status is `implemented`, within each surface's bounded support statement. Every profile currently marked `partial` or `specified` is named as an explicit non-claim; IntelliJ remains partial and LSP experimental. Tests derive the non-implemented profile set from the conformance manifest so a future profile/status change cannot silently drift from release-note scope.

## Deterministic release set

`python3 -m tools.release_bundle reproduce --output release-dist` builds twice from the same checked-out commit and rejects any file-set or byte difference. `SOURCE_DATE_EPOCH` comes from the source commit; `PYTHONHASHSEED=0`; the wheel uses the pinned M9-04 build backend without build isolation.

The output contains the versioned wheel, the scoped release-notes section, every tracked root `spec/*.json` contract, a manifest with source/tag/version/publication identity and SHA-256 values, `SHA256SUMS`, a deterministic normalized `.tar.gz`, and its sibling SHA-256 file. Validation rejects missing/additional artifacts, contract inventory drift, manifest/checksum drift, archive drift, or scoped-note drift.

## CI and publication semantics

`.github/workflows/release.yml` runs for pull requests to `main`, matching `aidl-toolchain-v*` tags, and manual dispatch. The `release-bundle` job has only repository-level `contents: read`, checks out the exact source SHA, validates the contract (binding `GITHUB_REF_NAME` when the event is a tag), reproduces the bundle, and uploads it as an Actions artifact.

A second `publish-github-prerelease` job runs only after that verified build succeeds and only when both conditions are true:

- `github.ref_type == 'tag'`;
- `github.ref_name == 'aidl-toolchain-v0.1.0rc1'`.

Only that job receives `contents: write`. It downloads the already verified bundle and runs `gh release create` with `--verify-tag` and `--prerelease`, attaching the deterministic archive/checksum and using the scoped notes file. A PR head, manual run, branch push, or differently named tag cannot reach public publication.

## First publication sequence

No tag or GitHub Release existed when M9-08 was implemented. The feature branch must merge through a green PR first. After integration, the precise publication step is to create and push annotated or lightweight tag `aidl-toolchain-v0.1.0rc1` pointing at the integrated `main` commit that contains this release contract. The tag-triggered workflow then rebuilds that exact commit and, only after verification succeeds, creates the GitHub pre-release.

Do not tag or publish an unreviewed feature head.

## Scope boundary

M9-08 changes the release version/tag/publication contract, scoped notes, deterministic bundle behavior, publication workflow, and matching support/conformance/roadmap documentation. M9-06 remains an administrative blocker and is not completed by this workflow. No Ruleset administration, signatures/attestations, SBOM, transparency log, or unsupported-profile stability promise is introduced.
