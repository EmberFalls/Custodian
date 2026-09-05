"""SQLite migration and upsert behavior with synthetic records."""

from custodian.core.enums import CaptureStatus, SourceType
from custodian.core.schemas import CapturePacketCounts, CaptureRecord
from custodian.storage import SQLiteRepository


def test_storage_initializes_required_tables_and_upserts_capture(tmp_path, observed_at) -> None:
    repository = SQLiteRepository(tmp_path / "runtime.sqlite3")
    repository.initialize()
    capture = CaptureRecord(
        capture_id="capture-test",
        source_type=SourceType.PCAP_REPLAY,
        display_name="fixture.cap",
        sha256="0" * 64,
        size_bytes=24,
        created_at=observed_at,
        first_packet_at=observed_at,
        last_packet_at=observed_at,
        status=CaptureStatus.READY,
        packet_counts=CapturePacketCounts(observed=1),
    )

    repository.upsert_capture(capture)
    repository.upsert_capture(capture)

    assert {
        "schema_migrations",
        "captures",
        "flow_summaries",
        "feature_window_references",
        "detector_results",
        "alerts",
        "evidence",
        "replay_checkpoints",
        "model_registry",
        "application_events",
    } <= repository.table_names()
