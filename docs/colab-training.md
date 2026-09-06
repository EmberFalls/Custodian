# Custodian Colab training workflow

## Purpose

Issue #1 adds a reproducible, isolated Google Colab workflow for the existing Behaviour model. The notebook:

1. pins dependency versions;
2. verifies those versions;
3. clones the public Custodian repository;
4. accepts only the three approved CICIDS2017 CSV files;
5. verifies schemas and label distributions;
6. reuses `custodian.features.behaviour_flow` through the existing training path;
7. requires Custodian's explicit isolated-training gate;
8. trains one XGBoost Behaviour model;
9. calibrates confidence on the held-out calibration split;
10. evaluates only after model/calibration/threshold selection is complete;
11. verifies exported artifact checksums;
12. creates a versioned model ZIP for temporary download;
13. removes temporary datasets and model artifacts from the Colab runtime.

## Security boundaries

The notebook never enables live packet capture, packet replay, traffic injection, payload execution, or local-network access. Do not upload credentials, private files, or unrelated personal data.

The training module independently requires both `--acknowledge-isolated-vm` and `CUSTODIAN_ISOLATED_TRAINING=YES`.

## Dataset

Use only the three filenames already accepted by `training/cicids2017.py`:

- `Friday-WorkingHours-Morning.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`

The official CICIDS2017 page is the authoritative source. Record the exact downloaded source, file size, SHA-256, and access date in the experiment record before treating a run as reproducible.

## Expected output

The model package contains:

- `model.json`
- `calibrator.joblib`
- `feature_schema.json`
- `class_mapping.json`
- `thresholds.json`
- `metrics.json`
- `manifest.json`

The repository already records the limitations of this dataset split. In particular, row blocks are provenance proxies, not verified host/session groups, so the resulting test score must not be presented as leakage-free streaming-PCAP accuracy.
