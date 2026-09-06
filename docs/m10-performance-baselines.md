# M10-07 deterministic performance baselines

M10-07 adds a versioned, reproducible compiler-scale regression contract without making CI depend on host timing noise.

## Contract and workloads

`spec/performance-baselines.json` is governed by `spec/performance-baselines.schema.json` (schema version 1). It defines exactly three synthetic Core workloads: `small`, `medium`, and `large`. `tools.performance_baselines` renders every workload from integer parameters only; there is no randomness, current time, machine identity, network input, or repository scan involved.

Each generated module is one `.aidl` file. Modules contain exported entities with deterministic fields, and every module after the first imports one declaration from its predecessor. The committed baselines therefore measure stable compiler work across source discovery/parsing and project indexing:

| Workload | Files | Source bytes | Declarations | Symbols | Import resolutions |
|---|---:|---:|---:|---:|---:|
| small | 4 | 4,745 | 32 | 32 | 3 |
| medium | 12 | 27,937 | 192 | 192 | 11 |
| large | 32 | 147,261 | 1,024 | 1,024 | 31 |

These values are exact outputs of the versioned renderer and compiler project model, not hand-estimated sizes. The gate also requires every metric to increase strictly from small to medium to large.

## Deterministic resource envelope

The same contract defines the CI resource envelope: at most 48 source files, 196,608 UTF-8 source bytes, 1,536 declarations, 1,536 symbol entries, and 48 import resolutions for these representative workloads. Every observed workload must remain inside the envelope, and each limit must remain no more than twice the current large baseline. This prevents both accidental baseline growth and silently making the limit effectively unbounded.

The envelope is a regression and reproducibility contract for representative compiler workloads. It is **not** a production parser/compiler rejection threshold, memory cap, throughput guarantee, latency SLA, or claim about maximum supported repository size. Runtime-enforced limits require a separate language/tooling contract so that exceeding them can produce a stable user-facing failure rather than an incidental internal error.

## Reproducing the measurement

Run:

```bash
python3 -m tools.performance_baselines measure
python3 -m tools.performance_baselines check
python3 -m unittest tools/test_performance_baselines.py
```

`measure` prints the currently observed deterministic metrics. `check` validates the JSON schema, exact baselines, byte-identical rendering, monotonic scale, and resource envelope. The normal `Compiler / Python` GitHub Actions job runs the check explicitly in addition to discovering the focused regression module.

Wall-clock duration is intentionally not a required gate. CI hosts, filesystem caches, CPU scheduling, and virtualization introduce noise that can turn a timing threshold into a flaky signal. Future timing benchmarks may be published as observational data, but a hard latency promise should be added only with a controlled benchmark environment and an explicit support contract.
