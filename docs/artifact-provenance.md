# Artifact provenance and integrity

This document describes only the provenance evidence that the repository currently produces. It does not claim signatures, attestations, an SBOM, a transparency log, or public release publication.

## Current artifact boundary

M9-05 builds a deterministic release bundle from one checked-out Git commit through `python3 -m tools.release_bundle reproduce --output release-dist`. The release control record is `release/release.json`; the package version comes from `pyproject.toml`; release notes come from committed `CHANGELOG.md`; JSON contracts are discovered from tracked root `spec/*.json` files.

For the current baseline, `release/release.json` declares:

- distribution `aidl-toolchain`;
- version `0.0.0`;
- tag identity `aidl-toolchain-v0.0.0`;
- `CHANGELOG.md` as the notes source;
- `spec/*.json` as the contract inventory;
- publication `disabled`.

The tag field is a release-contract identity. M9-05 does not create or move tags and does not publish a GitHub Release.

## Reproducibility evidence

The release builder derives the source identity from the checked-out Git `HEAD`, derives `SOURCE_DATE_EPOCH` from that commit timestamp, sets `PYTHONHASHSEED=0`, and builds with the exact M9-04 build-backend pins. `reproduce` performs two independent builds from the same checkout and rejects any difference in the output file set or bytes.

The deterministic archive normalizes ordering, ownership, modes, timestamps, and the gzip header. This establishes same-commit reproducibility for the implemented builder under the validated environment; it is not a cryptographic signer identity or a claim that every possible build environment has been proven equivalent.

## Manifest and checksums

The staged bundle contains a machine-readable `aidl-toolchain-<version>-release-manifest.json`. The manifest records:

- schema version;
- distribution, version, and configured tag identity;
- source Git commit and source-date epoch;
- publication state;
- wheel path and SHA-256;
- release-notes path, source path, and SHA-256;
- each tracked source contract path, release path, and SHA-256.

`SHA256SUMS` covers every staged release component except the checksum file itself. The sibling `<archive>.sha256` covers the deterministic `.tar.gz` archive. Validation also checks the exact expected stage/root file set, contract inventory, archive members, manifest values, and file bytes.

These SHA-256 values let a consumer detect byte changes relative to the manifest/checksum set. They do not authenticate who produced the files unless the source commit and checksum information are obtained through a separately trusted channel.

## CI evidence

`.github/workflows/release.yml` runs `Release Bundle / Dry Run` for pull requests to `main`, matching `aidl-toolchain-v*` tags, and manual dispatch. It checks out the exact PR head or tag commit, verifies the release contract, runs the same-commit reproduction check, and uploads the deterministic output as a GitHub Actions artifact.

The workflow has `contents: read` permission and no publication step. Its result is build/integrity evidence for that workflow run, not a public release or signed provenance statement.

## How to verify locally

On a supported Python 3.12 environment with the repository's pinned build backend available:

```bash
python3 -m tools.release_bundle verify-contract
python3 -m tools.release_bundle reproduce --output release-dist
```

For an actual tag-triggered source checkout, verification can additionally bind the expected tag identity:

```bash
python3 -m tools.release_bundle --tag aidl-toolchain-v0.0.0 verify-contract
python3 -m tools.release_bundle --tag aidl-toolchain-v0.0.0 reproduce --output release-dist
```

Inspect the generated manifest and compare SHA-256 values against the staged files/archive. The current tooling performs those consistency checks automatically during `reproduce`.

## Explicit non-claims

The current repository does **not** yet provide or claim:

- public artifact publication or the first scoped pre-release;
- cryptographic artifact or commit signing as part of this release contract;
- Sigstore/SLSA or other attestations;
- an SBOM;
- a transparency-log entry;
- a hosted provenance service;
- native `main` branch protection as an enforced release prerequisite.

Any future addition of those capabilities requires a separate roadmap change, implementation, validation, and updated documentation. M9-05 checksums and manifests must not be described as substitutes for signatures or attestations.
