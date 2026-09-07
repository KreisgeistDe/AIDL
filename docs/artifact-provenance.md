# Artifact provenance and integrity

This document describes only provenance and publication evidence the repository currently implements. It does not claim signatures, attestations, an SBOM, or a transparency log.

## Current artifact boundary

M9-08 builds a deterministic pre-release bundle from one checked-out Git commit through `python3 -m tools.release_bundle reproduce --output release-dist`. The release control record is `release/release.json`; package version comes from `pyproject.toml`; scoped release notes are extracted from committed `CHANGELOG.md`; JSON contracts are discovered from tracked root `spec/*.json` files.

The current contract declares distribution `aidl-toolchain`, version `0.1.0rc1`, tag `aidl-toolchain-v0.1.0rc1`, `CHANGELOG.md` as notes authority, `spec/*.json` as contract inventory, and publication `github-prerelease-on-tag`.

The tag identity is exact. Pull requests, branch heads, and manual workflow runs do not create or move tags and cannot publish a GitHub Release. Publication is possible only from a tag-triggered run whose tag exactly matches the configured release tag and whose deterministic bundle job succeeded.

## Reproducibility evidence

The release builder derives source identity and `SOURCE_DATE_EPOCH` from checked-out Git `HEAD`, sets `PYTHONHASHSEED=0`, and builds with the pinned M9-04 backend. `reproduce` performs two independent builds from the same checkout and rejects any output file-set or byte difference.

The deterministic archive normalizes ordering, ownership, modes, timestamps, and gzip header. This establishes same-commit reproducibility under the validated environment; it is not a cryptographic signer identity or proof of equivalence across every build environment.

## Manifest, notes, and checksums

The staged bundle contains `aidl-toolchain-<version>-release-manifest.json`. It records schema version, distribution/version/tag, source commit and epoch, publication mode, wheel path/checksum, scoped release-notes path/source/checksum, and each tracked source contract path/release path/checksum.

Only the current `## 0.1.0rc1 — scoped toolchain pre-release` changelog section is copied into release notes. Historical changelog sections are not part of the public notes payload.

`SHA256SUMS` covers every staged component except itself. The sibling `<archive>.sha256` covers the deterministic `.tar.gz`. Validation checks exact stage/root file sets, contract inventory, archive members, manifest values, scoped release-note bytes, and checksums.

These hashes detect byte changes relative to the manifest/checksum set. They do not authenticate a producer unless source identity and checksums are obtained through a separately trusted channel.

## CI and public pre-release publication

`.github/workflows/release.yml` first runs a read-only `Release Bundle / Verify` job for pull requests, release tags, and manual dispatch. It checks out the exact source SHA, verifies the version/tag contract, reproduces the bundle, and uploads the verified output as an Actions artifact.

The dependent publication job has `contents: write` only when the event is a tag and the tag is exactly `aidl-toolchain-v0.1.0rc1`. It downloads that verified artifact and uses `gh release create --verify-tag --prerelease`. Therefore publication cannot occur from an untagged feature head or from a differently named tag.

At implementation time there were no repository tags and no GitHub Releases. The first publication must happen only after the M9-08 PR is integrated: create and push `aidl-toolchain-v0.1.0rc1` at the integrated `main` commit containing this contract, then let the tag workflow verify and publish that exact commit.

## How to verify locally

On supported Python 3.12 with the pinned build backend available:

```bash
python3 -m tools.release_bundle verify-contract
python3 -m tools.release_bundle reproduce --output release-dist
```

For the actual release-tag checkout, bind the expected tag identity:

```bash
python3 -m tools.release_bundle --tag aidl-toolchain-v0.1.0rc1 verify-contract
python3 -m tools.release_bundle --tag aidl-toolchain-v0.1.0rc1 reproduce --output release-dist
```

## Explicit non-claims

The current repository does **not** claim cryptographic artifact/commit signing as part of this contract, Sigstore/SLSA attestations, an SBOM, a transparency-log entry, a hosted provenance service, general runtime support, stability for `partial`/`specified`/`experimental` surfaces, or native `main` protection as an enforced prerequisite.

M9-06 remains an administrative blocker. Checksums, deterministic builds, and GitHub pre-release publication must not be described as substitutes for signatures, attestations, or broader conformance.
