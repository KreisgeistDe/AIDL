# M9-05 reproducible release workflow

M9-05 defines a deterministic, read-only release-bundle workflow on top of the
M9-04 installable `aidl-toolchain` wheel. It does not publish a GitHub Release,
create or move tags, or enable branch protection.

## Version and tag contract

`release/release.json` is the versioned release control record. For schema
version 1 it must contain exactly:

- distribution `aidl-toolchain`;
- the same version as `[project].version` in `pyproject.toml`;
- tag `aidl-toolchain-v<version>`;
- versioned release-notes source `CHANGELOG.md`;
- contract inventory source `spec/*.json`;
- publication state `disabled`.

The current `0.0.0` value remains a non-published toolchain baseline. M9-05
makes that baseline reproducible; the later pre-release publication item owns a
future version bump, tag creation, publication enablement, and public release.
A tag-triggered dry run is accepted only when the actual tag exactly matches the
configured distribution/version pair.

`CHANGELOG.md` must contain the exact heading
`## <version> — unreleased toolchain baseline`. Release notes are copied byte for
byte from that committed source, so notes cannot be synthesized from mutable PR
or API state.

## Deterministic release set

`python3 -m tools.release_bundle reproduce --output release-dist` builds the
release twice from the same checked-out commit and rejects any byte difference.
The build derives `SOURCE_DATE_EPOCH` from the source commit timestamp and fixes
`PYTHONHASHSEED=0`; the wheel is built with the exact M9-04 setuptools/wheel
backend pins and no build isolation.

The output contains exactly:

- directory `aidl-toolchain-<version>-release/`;
- `aidl_toolchain-<version>-py3-none-any.whl`;
- `contracts/<original-name>.json` for every tracked root `spec/*.json` file,
  sorted deterministically and with no hand-maintained allowlist;
- `aidl-toolchain-<version>-release-notes.md` copied from `CHANGELOG.md`;
- `aidl-toolchain-<version>-release-manifest.json` recording source commit,
  source epoch, tag/version identity, wheel checksum, release-notes checksum,
  and every source/release contract path plus SHA-256;
- `SHA256SUMS` over every staged component except itself;
- deterministic `aidl-toolchain-<version>-release.tar.gz` with normalized
  ownership, modes, ordering, timestamps and gzip header;
- sibling `.tar.gz.sha256` checksum.

Validation rejects missing or additional root/stage artifacts, contract-set
mismatch, manifest drift, checksum drift, archive-member drift, wrong
version/tag identity, and any byte mismatch across the two independent builds.
A newly committed `spec/*.json` file is automatically required in the release
set; deleting one removes it from the source-of-truth inventory.

## CI dry run

`.github/workflows/release.yml` runs `Release Bundle / Dry Run` for pull requests
to `main`, matching release tags, and manual dispatches. It checks out the exact
PR head or tag commit with full history, installs only the pinned M9-04 build
backend, verifies the release contract, reproduces the bundle twice, and uploads
the resulting deterministic directory as an Actions artifact.

The workflow has only `contents: read`. A tag run therefore proves that a tagged
commit can reproduce the exact bundle without publishing it. Actual GitHub
Release creation, public artifact publication, provenance/attestation policy,
and the first scoped pre-release remain later M9 work.

## Focused regression coverage

`tools/test_release_bundle.py` is discovered by the existing M9-01 Python test
selector. It covers wrong package version, wrong tag, deterministic automatic
contract inventory, missing release files, unexpected artifacts, and
non-reproducible bytes. The full Actions dry run additionally proves the real
wheel, complete current JSON-contract set, release manifest, archive and
checksums from the project head.

## Scope boundary

M9-05 changes release construction only. Existing Validation, Compatibility,
Golden Fixtures, Petstore Runtime/PostgreSQL, IntelliJ, packaging smoke and
`.ai/**` boundary checks remain unchanged. Branch protection, contribution and
security/support/provenance documentation, and actual public pre-release
publication remain separate open roadmap items.
