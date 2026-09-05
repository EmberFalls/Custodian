"""Local-only command boundary for Custodian."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from custodian.config import load_config_bundle
from custodian.core.enums import ReplayMode
from custodian.ingestion.validation import CaptureValidator
from custodian.runtime.engine import CustodianEngine


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="custodian",
        description="Passive, local-first network observation",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    api = subcommands.add_parser("api", help="start the loopback-only API")
    api.add_argument("--port", type=int, default=8000)
    replay = subcommands.add_parser("replay", help="read an authorized local capture")
    replay.add_argument("--pcap", type=Path, required=True)
    replay.add_argument("--mode", choices=[mode.value for mode in ReplayMode], default="fast")
    replay.add_argument("--speed", type=float, default=1.0)
    subcommands.add_parser("safety-status", help="show enforced phase gates")
    for name in ("prepare-data", "train", "live"):
        subcommands.add_parser(name, help="intentionally gated pending explicit approval")
    return parser


def _gated(command: str) -> int:
    messages = {
        "prepare-data": "Dataset preparation is gated to the approved isolated VM workflow.",
        "train": "Model training is gated until the isolated VM and datasets are explicitly approved.",
        "live": "Passive live capture is not enabled; PCAP replay must be completed and approved first.",
    }
    print(messages[command])
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command in {"prepare-data", "train", "live"}:
        return _gated(args.command)
    if args.command == "safety-status":
        print(
            json.dumps(
                {
                    "passive_only": True,
                    "api_bind": "127.0.0.1",
                    "outbound_traffic_path": False,
                    "model_training": "gated",
                    "live_capture": "gated",
                    "artifact_trust_default": False,
                },
                indent=2,
            )
        )
        return 0
    if args.command == "api":
        if not 1 <= args.port <= 65535:
            raise SystemExit("port must be between 1 and 65535")
        import uvicorn

        uvicorn.run("custodian.api.app:app", host="127.0.0.1", port=args.port)
        return 0
    capture = args.pcap.resolve()
    config = load_config_bundle(root / "configs")
    validator = CaptureValidator(
        capture.parent, max_size_bytes=config.replay.max_capture_size_bytes
    )
    validator.validate(capture.name)
    engine = CustodianEngine(config)
    list(engine.replay(capture, mode=ReplayMode(args.mode), speed_multiplier=args.speed))
    print(
        json.dumps(
            {
                "capture": capture.name,
                "metrics": engine.metrics.snapshot(force=True),
                "detectors": engine.detector_status(),
                "alerts": [alert.model_dump(mode="json") for alert in engine.alerts],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
