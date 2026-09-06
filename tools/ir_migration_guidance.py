from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from tools.ir_compatibility import (
    IrCompatibilityClassification,
    classify_ir_diff,
)
from tools.ir_diff import IrDiffChange, diff_canonical_ir


MigrationPhaseName = Literal[
    "expand",
    "deployReaders",
    "backfill",
    "switchWrites",
    "verify",
    "contract",
]

_PHASE_ORDER: dict[MigrationPhaseName, int] = {
    "expand": 0,
    "deployReaders": 1,
    "backfill": 2,
    "switchWrites": 3,
    "verify": 4,
    "contract": 5,
}


class IrMigrationGuidanceError(ValueError):
    """Raised when guidance inputs are not authoritative for the supplied IR states."""


@dataclass(frozen=True)
class IrMigrationPhase:
    phase: MigrationPhaseName
    action: str
    evidence: str

    def to_json(self) -> dict[str, str]:
        return {
            "phase": self.phase,
            "action": self.action,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class IrMigrationGuidance:
    kind: str
    path: str
    classification: str
    classification_rule: str
    phases: tuple[IrMigrationPhase, ...]
    preconditions: tuple[str, ...]
    note: str

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "classification": self.classification,
            "classificationRule": self.classification_rule,
            "phases": [phase.to_json() for phase in self.phases],
            "preconditions": list(self.preconditions),
            "note": self.note,
        }


def _phase(
    phase: MigrationPhaseName,
    action: str,
    evidence: str,
) -> IrMigrationPhase:
    return IrMigrationPhase(phase=phase, action=action, evidence=evidence)


def _ordered(phases: Sequence[IrMigrationPhase]) -> tuple[IrMigrationPhase, ...]:
    ordered = tuple(sorted(phases, key=lambda item: _PHASE_ORDER[item.phase]))
    names = [item.phase for item in ordered]
    if len(names) != len(set(names)):
        raise IrMigrationGuidanceError("migration guidance contains a duplicate rollout phase")
    return ordered


def _required_field_guidance(
    change: IrDiffChange,
    classification: IrCompatibilityClassification,
) -> IrMigrationGuidance:
    evidence = f"{classification.rule} at {change.path}"
    phases = _ordered(
        [
            _phase(
                "expand",
                "Expand the persisted schema so the new required contract can coexist with the old contract during rollout.",
                evidence,
            ),
            _phase(
                "deployReaders",
                "Deploy readers that tolerate the expanded persisted representation before changing write requirements.",
                evidence,
            ),
            _phase(
                "backfill",
                "Backfill existing stored records so they satisfy the new required-field contract.",
                evidence,
            ),
            _phase(
                "switchWrites",
                "Switch writers to always satisfy the new required-field contract after backfill readiness is established.",
                evidence,
            ),
            _phase(
                "verify",
                "Verify existing and newly written records satisfy the new required-field contract before contraction.",
                evidence,
            ),
            _phase(
                "contract",
                "Enforce the final required-field contract only after verification succeeds.",
                evidence,
            ),
        ]
    )
    return IrMigrationGuidance(
        kind=change.kind,
        path=change.path,
        classification=classification.classification,
        classification_rule=classification.rule,
        phases=phases,
        preconditions=(
            "Define and approve the backfill value or derivation externally; Canonical IR does not encode a value source or executable backfill mechanism.",
        ),
        note="The rollout sequence is evidence-backed, but no SQL, data transform, or backfill implementation is inferred.",
    )


def _field_added_guidance(
    change: IrDiffChange,
    classification: IrCompatibilityClassification,
) -> IrMigrationGuidance:
    evidence = f"{classification.rule} at {change.path}"
    phases = _ordered(
        [
            _phase(
                "expand",
                "Add the persisted field while preserving the existing stored contract during rollout.",
                evidence,
            ),
            _phase(
                "deployReaders",
                "Deploy readers that tolerate the expanded persisted representation before relying on the new field.",
                evidence,
            ),
            _phase(
                "switchWrites",
                "Begin writing the new field only after the expanded schema and compatible readers are deployed.",
                evidence,
            ),
            _phase(
                "verify",
                "Verify old and new application versions can operate against the expanded persisted representation.",
                evidence,
            ),
        ]
    )
    return IrMigrationGuidance(
        kind=change.kind,
        path=change.path,
        classification=classification.classification,
        classification_rule=classification.rule,
        phases=phases,
        preconditions=(),
        note="No backfill is proposed because the authoritative classification does not prove one is required.",
    )


def _constraint_guidance(
    change: IrDiffChange,
    classification: IrCompatibilityClassification,
) -> IrMigrationGuidance:
    evidence = f"{classification.rule} at {change.path}"
    phases = _ordered(
        [
            _phase(
                "expand",
                "Prepare the persisted schema change without assuming an executable data rewrite.",
                evidence,
            ),
            _phase(
                "verify",
                "Verify stored data and application behavior against the proposed persisted constraint before final enforcement.",
                evidence,
            ),
            _phase(
                "contract",
                "Apply the final persisted constraint only after verification establishes that the new contract is satisfiable.",
                evidence,
            ),
        ]
    )
    return IrMigrationGuidance(
        kind=change.kind,
        path=change.path,
        classification=classification.classification,
        classification_rule=classification.rule,
        phases=phases,
        preconditions=(
            "If stored data does not satisfy the target constraint, define an explicit remediation/backfill plan; Canonical IR does not encode that transformation.",
        ),
        note="Constraint sequencing is suggested from persisted-schema evidence only; no data-conversion implementation is invented.",
    )


def _required_relaxed_guidance(
    change: IrDiffChange,
    classification: IrCompatibilityClassification,
) -> IrMigrationGuidance:
    evidence = f"{classification.rule} at {change.path}"
    phases = _ordered(
        [
            _phase(
                "expand",
                "Relax the persisted schema so old and new application versions can coexist during rollout.",
                evidence,
            ),
            _phase(
                "deployReaders",
                "Deploy readers that tolerate the relaxed persisted contract before writers rely on it.",
                evidence,
            ),
            _phase(
                "switchWrites",
                "Allow writers to use the relaxed contract only after compatible readers are deployed.",
                evidence,
            ),
            _phase(
                "verify",
                "Verify mixed-version application behavior against the relaxed persisted contract.",
                evidence,
            ),
        ]
    )
    return IrMigrationGuidance(
        kind=change.kind,
        path=change.path,
        classification=classification.classification,
        classification_rule=classification.rule,
        phases=phases,
        preconditions=(),
        note="No backfill or destructive contraction is inferred from a requiredness relaxation.",
    )


def _guidance_for(
    change: IrDiffChange,
    classification: IrCompatibilityClassification,
) -> IrMigrationGuidance:
    if classification.classification == "safe":
        return IrMigrationGuidance(
            kind=change.kind,
            path=change.path,
            classification="safe",
            classification_rule=classification.rule,
            phases=(),
            preconditions=(),
            note="The proved safe classification does not require migration sequencing.",
        )

    if classification.classification == "conditional":
        return IrMigrationGuidance(
            kind=change.kind,
            path=change.path,
            classification="conditional",
            classification_rule=classification.rule,
            phases=(),
            preconditions=(
                f"Review and coordinate this change before rollout because {classification.rule} is conditional: {classification.reason}",
            ),
            note="No migration phases are proposed because compatibility depends on evidence or coordination not represented in Canonical IR.",
        )

    if classification.classification == "breaking":
        return IrMigrationGuidance(
            kind=change.kind,
            path=change.path,
            classification="breaking",
            classification_rule=classification.rule,
            phases=(),
            preconditions=(
                f"Obtain explicit compatibility review and approval for the breaking change classified by {classification.rule}.",
                "Define and test a rollback/recovery procedure before rollout.",
                "If persisted state can be affected, create and verify a recoverable backup or equivalent recovery point before destructive work.",
            ),
            note="No apparently safe expand/backfill/contract automation is emitted for a breaking change.",
        )

    if classification.rule in {"entity.required-field-added", "entity.field-required-tightened"}:
        return _required_field_guidance(change, classification)
    if classification.rule == "entity.field-added":
        return _field_added_guidance(change, classification)
    if classification.rule == "entity.constraint-changed":
        return _constraint_guidance(change, classification)
    if classification.rule == "entity.field-required-relaxed":
        return _required_relaxed_guidance(change, classification)

    return IrMigrationGuidance(
        kind=change.kind,
        path=change.path,
        classification=classification.classification,
        classification_rule=classification.rule,
        phases=(),
        preconditions=(
            f"Provide an explicit migration plan for {classification.rule}; M7-05 has no Canonical-IR evidence for a safe rollout sequence for this migration-required rule.",
        ),
        note="The migration requirement is authoritative, but missing sequencing evidence is kept explicit rather than guessed.",
    )


def build_ir_migration_guidance(
    changes: Sequence[IrDiffChange],
    classifications: Sequence[IrCompatibilityClassification],
    old_document: Mapping[str, Any],
    new_document: Mapping[str, Any],
) -> list[IrMigrationGuidance]:
    """Build deterministic migration guidance from authoritative diff/classification evidence."""

    supplied_changes = list(changes)
    authoritative_changes = diff_canonical_ir(old_document, new_document)
    if supplied_changes != authoritative_changes:
        raise IrMigrationGuidanceError(
            "diff facts do not match the authoritative M7-01 diff for the supplied Canonical IR states"
        )

    supplied_classifications = list(classifications)
    authoritative_classifications = classify_ir_diff(
        authoritative_changes,
        old_document,
        new_document,
    )
    if supplied_classifications != authoritative_classifications:
        raise IrMigrationGuidanceError(
            "classifications do not match the authoritative M7 compatibility result for the supplied Canonical IR states"
        )

    if len(supplied_changes) != len(supplied_classifications):
        raise IrMigrationGuidanceError("diff fact and classification counts do not match")

    return [
        _guidance_for(change, classification)
        for change, classification in zip(supplied_changes, supplied_classifications, strict=True)
    ]


def ir_migration_guidance_to_json(
    guidance: Sequence[IrMigrationGuidance],
) -> list[dict[str, Any]]:
    return [item.to_json() for item in guidance]
