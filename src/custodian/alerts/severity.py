"""Small configuration-driven severity policy."""

from __future__ import annotations

from custodian.core.enums import Severity, ThreatClass


def select_severity(threat_class: ThreatClass, rules: dict[str, str]) -> Severity:
    """Resolve a configured severity without conflating it with confidence."""

    configured = rules.get(threat_class.value, rules.get("UNKNOWN", Severity.LOW.value))
    return Severity(configured)
