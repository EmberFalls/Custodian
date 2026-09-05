"""Exports use local synthetic database records only."""

import csv
import json

from custodian.exports.service import ExportService, escape_spreadsheet_value
from custodian.storage import SQLiteRepository


def test_spreadsheet_formula_prefixes_are_escaped() -> None:
    assert escape_spreadsheet_value("=cmd") == "'=cmd"
    assert escape_spreadsheet_value("ordinary") == "ordinary"


def test_empty_exports_are_bounded_to_output_root(tmp_path) -> None:
    repository = SQLiteRepository(tmp_path / "runtime.sqlite3")
    repository.initialize()
    output = tmp_path / "reports"
    service = ExportService(repository, output)

    json_path = service.export_alerts("json")
    csv_path = service.export_alerts("csv")

    assert json_path.parent == output.resolve()
    assert csv_path.parent == output.resolve()
    with csv_path.open(encoding="utf-8") as stream:
        header = next(csv.reader(stream))
        assert "alert_id" in header
        assert "configuration_fingerprint" in header
    document = json.loads(json_path.read_text(encoding="utf-8"))
    assert document["application"] == "Custodian"
    assert document["mock_status"] is False


def test_endpoint_anonymization_is_stable_within_one_export() -> None:
    source = {"source": {"ip": "10.0.0.1", "port": 1234}}

    first = ExportService._anonymize_alert(source, b"test-salt")
    second = ExportService._anonymize_alert(source, b"test-salt")

    assert first == second
    assert first["source"]["ip"].startswith("host-")
    assert "10.0.0.1" not in json.dumps(first)
