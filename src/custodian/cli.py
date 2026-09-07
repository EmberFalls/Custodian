"""Local-only command boundary for Custodian."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import warnings
from pathlib import Path

from custodian.config import load_config_bundle
from custodian.core.enums import ReplayMode
from custodian.ingestion.validation import CaptureValidator
from custodian.runtime.engine import CustodianEngine


def _ensure_training_importable(root: Path) -> None:
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


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
    subcommands.add_parser(
        "demo-check",
        help="verify pinned dependencies and configured detector readiness",
    )
    prepare = subcommands.add_parser(
        "prepare-data", help="prepare DGA data in an approved isolated environment"
    )
    prepare.add_argument("--family", choices=("dga",), required=True)
    prepare.add_argument("--data-dir", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--manifest", type=Path, default=None)
    prepare.add_argument("--max-rows-per-class", type=int, default=None)
    prepare.add_argument("--acknowledge-isolated-vm", action="store_true")
    train = subcommands.add_parser(
        "train", help="train a DGA candidate in an approved isolated environment"
    )
    train.add_argument("family", choices=("dga",))
    train.add_argument("--input-path", type=Path, required=True)
    train.add_argument("--output-dir", type=Path, required=True)
    train.add_argument("--feature-set", choices=("full", "lexical", "original"), default="lexical")
    train.add_argument("--acknowledge-isolated-vm", action="store_true")
    subcommands.add_parser("live", help="intentionally gated pending explicit approval")
    return parser


def _demo_constraints(path: Path) -> dict[str, str]:
    constraints: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        package, version = line.split("==", maxsplit=1)
        constraints[package.strip()] = version.strip()
    return constraints


def _run_demo_check(root: Path) -> int:
    expected_dependencies = _demo_constraints(root / "constraints-demo.txt")
    dependencies: dict[str, dict[str, str | bool | None]] = {}
    for package, expected in expected_dependencies.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        dependencies[package] = {
            "expected": expected,
            "actual": actual,
            "matches": actual == expected,
        }

    config = load_config_bundle(root / "configs")
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        engine = CustodianEngine(config)
    detectors = engine.detector_status()
    artifact_runtime_warnings = [
        str(item.message)
        for item in caught_warnings
        if item.category.__name__ == "InconsistentVersionWarning"
    ]
    artifact_serialization_versions = sorted(
        {
            message.split(" from version ", maxsplit=1)[1].split(
                " when using version ", maxsplit=1
            )[0]
            for message in artifact_runtime_warnings
            if " from version " in message and " when using version " in message
        }
    )
    ready_detectors = [
        detector
        for detector in detectors
        if detector.get("enabled") and detector.get("status") == "READY"
    ]
    dependencies_match = all(item["matches"] for item in dependencies.values())
    all_detectors_ready = len(detectors) == 4 and len(ready_detectors) == 4
    report = {
        "ready": dependencies_match and all_detectors_ready,
        "localhost_only": True,
        "dependencies_match": dependencies_match,
        "dependencies": dependencies,
        "detectors_ready": f"{len(ready_detectors)}/{len(detectors)}",
        "artifact_serialization_versions": artifact_serialization_versions,
        "artifact_version_warning_count": len(artifact_runtime_warnings),
        "detectors": detectors,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 2


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
    if args.command == "live":
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
    if args.command == "demo-check":
        return _run_demo_check(root)
    if args.command in {"prepare-data", "train"}:
        _ensure_training_importable(root)
        from training.commands import prepare_dga, train_dga

        try:
            if args.command == "prepare-data":
                destination = prepare_dga(
                    args.data_dir,
                    args.output,
                    manifest_path=args.manifest,
                    max_rows_per_class=args.max_rows_per_class,
                    isolation_acknowledged=args.acknowledge_isolated_vm,
                )
            else:
                destination = train_dga(
                    args.input_path,
                    output_dir=args.output_dir,
                    feature_set=args.feature_set,
                    isolation_acknowledged=args.acknowledge_isolated_vm,
                )
        except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
            print(f"{args.command} stopped: {exc}")
            return 2
        print(json.dumps({"output": str(destination)}, indent=2))
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
