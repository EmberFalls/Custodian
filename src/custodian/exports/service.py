"""Generate bounded JSON/CSV reports without accepting arbitrary output paths."""

from __future__ import annotations

import csv
import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from custodian.storage import SQLiteRepository


def escape_spreadsheet_value(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


class ExportService:
    """Write reports only beneath a configured local output directory."""

    def __init__(self, repository: SQLiteRepository, output_root: str | Path) -> None:
        self.repository = repository
        self.output_root = Path(output_root).resolve()

    @staticmethod
    def _anonymize_alert(alert: dict, salt: bytes) -> dict:
        anonymized = dict(alert)
        for field in ("source", "destination"):
            endpoint = anonymized.get(field)
            if not isinstance(endpoint, dict) or endpoint.get("ip") is None:
                continue
            endpoint = dict(endpoint)
            digest = hashlib.sha256(salt + str(endpoint["ip"]).encode("utf-8")).hexdigest()
            endpoint["ip"] = f"host-{digest[:16]}"
            anonymized[field] = endpoint
        return anonymized

    def export_alerts(
        self,
        format_name: str,
        *,
        metadata: dict[str, object] | None = None,
        anonymize: bool = False,
    ) -> Path:
        if format_name not in {"json", "csv"}:
            raise ValueError("export format must be json or csv")
        self.output_root.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(UTC)
        name = f"custodian-alerts-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.{format_name}"
        destination = (self.output_root / name).resolve()
        destination.relative_to(self.output_root)
        alerts = self.repository.export_alerts()
        if anonymize:
            salt = secrets.token_bytes(32)
            alerts = [self._anonymize_alert(alert, salt) for alert in alerts]
        provenance = {
            "application": "Custodian",
            "application_version": "0.3.0",
            "mock_status": False,
            "anonymized": anonymize,
            **(metadata or {}),
        }
        if format_name == "json":
            document = {
                "generated_at": generated_at.isoformat(),
                **provenance,
                "passive_only": True,
                "limitations": [
                    "Exported assessments depend on the models and evidence available at runtime."
                ],
                "alerts": alerts,
            }
            destination.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
            return destination
        columns = (
            "generated_at",
            "application_version",
            "configuration_fingerprint",
            "capture_sha256",
            "active_models_json",
            "mock_status",
            "anonymized",
            "alert_id",
            "capture_id",
            "timestamp",
            "threat_class",
            "severity",
            "decision",
            "status",
            "threat_confidence",
            "observation_confidence",
            "detector_id",
            "model_version",
            "feature_schema_version",
            "source",
            "destination",
            "limitations",
        )
        with destination.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for alert in alerts:
                row = {column: alert.get(column) for column in columns}
                row.update(
                    {
                        "generated_at": generated_at.isoformat(),
                        "application_version": provenance["application_version"],
                        "configuration_fingerprint": provenance.get("configuration_fingerprint"),
                        "capture_sha256": provenance.get("capture_sha256"),
                        "active_models_json": json.dumps(
                            provenance.get("models", []), sort_keys=True
                        ),
                        "mock_status": provenance["mock_status"],
                        "anonymized": provenance["anonymized"],
                    }
                )
                for nested in ("source", "destination", "limitations"):
                    row[nested] = json.dumps(row[nested], sort_keys=True)
                writer.writerow(
                    {key: escape_spreadsheet_value(value) for key, value in row.items()}
                )
        return destination
