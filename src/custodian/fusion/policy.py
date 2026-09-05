"""Conservative fusion that never invents a more specific threat class."""

from __future__ import annotations

from dataclasses import dataclass

from custodian.core.enums import AlertDecision, ThreatClass
from custodian.core.schemas import DetectorVerdict
from custodian.evidence.gate import GateResult


@dataclass(frozen=True, slots=True)
class FusedAssessment:
    decision: AlertDecision | None
    threat_class: ThreatClass | None
    threat_confidence: float | None
    observation_confidence: float | None
    contributor_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()


class FusionPolicy:
    """Fuse evidence-gated results without treating detector scores as independent."""

    version = "fusion.v1"

    def fuse(self, candidates: list[tuple[DetectorVerdict, GateResult]]) -> FusedAssessment:
        accepted = [
            (verdict, gate) for verdict, gate in candidates if gate.decision is AlertDecision.ACCEPT
        ]
        if accepted:
            classes = {verdict.threat_class for verdict, _ in accepted}
            ids = tuple(verdict.detector_id for verdict, _ in accepted)
            observation = [
                verdict.observation_confidence
                for verdict, _ in accepted
                if verdict.observation_confidence is not None
            ]
            if len(classes) > 1:
                return FusedAssessment(
                    AlertDecision.UNKNOWN_SUSPICIOUS,
                    None,
                    max(verdict.threat_confidence or 0 for verdict, _ in accepted),
                    min(observation) if observation else None,
                    ids,
                    ("accepted detectors disagree on the supported threat class",),
                )
            return FusedAssessment(
                AlertDecision.ACCEPT,
                next(iter(classes)),
                max(verdict.threat_confidence or 0 for verdict, _ in accepted),
                min(observation) if observation else None,
                ids,
            )
        unknown = [
            item for item in candidates if item[1].decision is AlertDecision.UNKNOWN_SUSPICIOUS
        ]
        if unknown:
            return FusedAssessment(
                AlertDecision.UNKNOWN_SUSPICIOUS,
                None,
                max(item[0].threat_confidence or 0 for item in unknown),
                min(
                    (
                        item[0].observation_confidence
                        for item in unknown
                        if item[0].observation_confidence is not None
                    ),
                    default=None,
                ),
                tuple(item[0].detector_id for item in unknown),
            )
        insufficient = [
            item for item in candidates if item[1].decision is AlertDecision.INSUFFICIENT_EVIDENCE
        ]
        if insufficient:
            return FusedAssessment(
                AlertDecision.INSUFFICIENT_EVIDENCE,
                None,
                None,
                min(
                    (
                        item[0].observation_confidence
                        for item in insufficient
                        if item[0].observation_confidence is not None
                    ),
                    default=None,
                ),
                tuple(item[0].detector_id for item in insufficient),
                tuple(
                    dict.fromkeys(
                        reason for _, gate in insufficient for reason in gate.missing_evidence
                    )
                ),
            )
        return FusedAssessment(None, None, None, None, ())
