"""Local-only command boundary for Custodian."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from custodian.config import load_config_bundle
from custodian.core.enums import ReplayMode
from custodian.ingestion.validation import CaptureValidator
from custodian.runtime.engine import CustodianEngine


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_training_importable(root: Path) -> None:
    """Allow `training.*` imports from a source checkout or editable install."""

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


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

    prepare = subcommands.add_parser(
        "prepare-data",
        help="prepare a versioned training table (isolated VM only)",
    )
    prepare.add_argument(
        "--family",
        required=True,
        help="behaviour|behavior, dns, or tls_quic|encrypted-session",
    )
    prepare.add_argument("--data-dir", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--manifest", type=Path, default=None)
    prepare.add_argument("--max-rows-per-class", type=int, default=None)
    prepare.add_argument(
        "--acknowledge-isolated-vm",
        action="store_true",
        help="confirm the isolated-VM checklist; also requires CUSTODIAN_ISOLATED_TRAINING=YES",
    )

    train = subcommands.add_parser(
        "train",
        help="train a model family (isolated VM only)",
    )
    train.add_argument(
        "family",
        help="behaviour|behavior, dns, or tls_quic|encrypted-session",
    )
    train.add_argument("--data-dir", type=Path, default=None)
    train.add_argument("--input-path", type=Path, default=None)
    train.add_argument("--output-dir", type=Path, default=None)
    train.add_argument(
        "--feature-set",
        choices=("full", "top12", "original"),
        default="full",
        help="dns feature subset (ignored by other families)",
    )
    train.add_argument("--n-jobs", type=int, default=None)
    train.add_argument(
        "--prepare-only",
        action="store_true",
        help="behaviour only: prepare processed table without fitting a model",
    )
    train.add_argument(
        "--acknowledge-isolated-vm",
        action="store_true",
        help="confirm the isolated-VM checklist; also requires CUSTODIAN_ISOLATED_TRAINING=YES",
    )

    live = subcommands.add_parser("live", help="intentionally gated pending explicit approval")
    live.add_argument("--config", type=Path, default=None)
    live.add_argument("--interface", default=None)
    return parser


def _gated_live() -> int:
    print(
        "Passive live capture is not enabled; PCAP replay must be completed and approved first."
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = _repo_root()

    if args.command == "live":
        return _gated_live()

    if args.command == "safety-status":
        print(
            json.dumps(
                {
                    "passive_only": True,
                    "api_bind": "127.0.0.1",
                    "outbound_traffic_path": False,
                    "model_training": "gated_until_isolated_vm_acknowledgement",
                    "live_capture": "gated",
                    "artifact_trust_default": False,
                    "prepare_train_entrypoint": "custodian prepare-data|train",
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

    if args.command == "prepare-data":
        _ensure_training_importable(root)
        from training.commands import prepare_data

        try:
            prepare_data(
                family=args.family,
                data_dir=args.data_dir,
                output_path=args.output,
                isolation_acknowledged=args.acknowledge_isolated_vm,
                max_rows_per_class=args.max_rows_per_class,
                manifest_path=args.manifest,
            )
        except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
            print(f"Prepare stopped: {exc}")
            return 2
        return 0

    if args.command == "train":
        _ensure_training_importable(root)
        from training.commands import train_model

        try:
            destination = train_model(
                family=args.family,
                isolation_acknowledged=args.acknowledge_isolated_vm,
                data_dir=args.data_dir,
                input_path=args.input_path,
                output_dir=args.output_dir,
                feature_set=args.feature_set,
                n_jobs=args.n_jobs,
                prepare_only=args.prepare_only,
            )
        except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
            print(f"Training stopped: {exc}")
            return 2
        print(json.dumps({"artifacts": str(destination)}, indent=2))
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
