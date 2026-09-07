# Custodian dataset provenance requirements

## Status

Issue #1 does not approve or download any dataset. This document defines the record every later model issue must create before preparation or fitting.

Dataset names and links below identify candidates or selected sources. A link alone is not approval. The model pull request must record the exact revision/files used, validate label meaning and feature compatibility, and obtain data-governance review.

## Candidate source register

| Model family | Source | Official/project page | Intended use | Current status |
| --- | --- | --- | --- | --- |
| Behaviour | CICIDS2017 MachineLearningCSV | <https://www.unb.ca/cic/datasets/ids-2017.html> | DDoS, recon, and broad bot/C2-like flow labels | Selected for Issue #2; run-specific files/hashes still required |
| DNS DGA | harpomaxx DGA Detection | <https://huggingface.co/datasets/harpomaxx/dga-detection> | Binary benign/DGA-like training with family-aware evaluation | Candidate selected for Issue #3; adapter and revision review required |
| DNS DGA | ExtraHop DGA Detection Training Dataset | <https://github.com/ExtraHop/DGA-Detection-Training-Dataset> | Optional external binary comparison | Candidate only; do not merge blindly with the primary source |
| DNS tunnelling development | BCCC-CIC-Bell-DNS-2024 | <https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/malicious-dns-and-attacks-bccc-cic-bell-dns-2024/> | Raw DNS metadata, grouped development splits, and a separate diagnostic holdout | Selected for Issue #4; exact files and hashes are generated in hosted Colab |
| DNS tunnelling final evaluation | DNS Threats Dataset v1 | <https://doi.org/10.5281/zenodo.6508640> | Immutable `test_combined_multiclass.csv.gz` domain/class split; classes 0 and 2 only | Selected and locked before candidate fitting; published MD5 and Custodian SHA-256 required |
| DNS tunnelling rejected final source | DNSTunnel2026 | <https://doi.org/10.5281/zenodo.20137065> | Considered for independent operational evaluation | Rejected: published archive contains processed engineered features, not the described raw DNS schema; bundled model is forbidden |
| TLS/QUIC | CipherSpectrum | <https://cgi.cse.unsw.edu.au/~cspectrum/> | TLS 1.3 encrypted-session research | Candidate for Issue #5; PCAP handling and license review required |
| TLS/QUIC | CESNET DataZoo | <https://cesnet.github.io/cesnet-datazoo/datasets_overview/> | TLS/QUIC flow metadata and evaluation | Candidate for Issue #5 |

## Required manifest fields

Every actual dataset run must export a machine-readable manifest containing:

```json
{
  "manifest_version": "custodian.dataset.v1",
  "detector_family": "dns",
  "feature_schema_version": "dns.v1",
  "dataset_name": "source-defined name",
  "canonical_source_url": "https://example.invalid/dataset",
  "source_revision": "immutable revision or release identifier",
  "accessed_at_utc": "ISO-8601 timestamp",
  "license": "source-declared license identifier and URL",
  "files": [
    {
      "name": "source filename",
      "bytes": 0,
      "sha256": "64 lowercase hexadecimal characters"
    }
  ],
  "source_schema": {},
  "source_label_meanings": {},
  "custodian_label_mapping": {},
  "row_counts_before_cleaning": {},
  "row_counts_after_cleaning": {},
  "invalid_rows_removed": 0,
  "duplicates_removed": 0,
  "conflicts_removed": 0,
  "grouping_and_split_identity": "separate manifest reference",
  "known_leakage_risks": [],
  "known_domain_shift": [],
  "approval": {
    "state": "candidate",
    "reviewer": null,
    "reviewed_at_utc": null
  }
}
```

Do not copy the illustrative values above into a real run. Generate counts and hashes from the exact received data.

## DNS DGA-specific requirements

For the selected Hugging Face candidate:

- runtime scope is initially binary `BENIGN` versus `DGA_LIKE`;
- preserve family labels for grouping, audit, per-family recall, and whole-family holdout;
- do not claim family attribution from the binary runtime detector;
- never visit, resolve, ping, enrich, or otherwise contact listed domains;
- treat domains as inert strings;
- normalize before deduplication and splitting;
- keep identical normalized domains in one split;
- report known-family and completely held-out-family results separately; and
- do not use source, family, row ID, or label as a predictive feature.

The source dataset is domain text, not a prepared Custodian `dns.v1` feature table. Issue #3 must provide a reviewed adapter through the shared DNS feature extractor. If runtime DNS features require evidence absent from domain-only rows, the schema mismatch must be resolved explicitly rather than filling missing evidence with invented values.

## Security and storage rules

- Download and process datasets only in the approved hosted Colab/model environment.
- Prefer CSV, JSON, or Parquet metadata to raw PCAPs where the model permits.
- Do not execute dataset contents or companion scripts.
- Do not replay PCAP traffic or contact indicators in a dataset.
- Do not mount the developer's full machine or Drive.
- Do not commit raw data, prepared tables, trained artifacts, metrics containing sensitive rows, or private paths.
- Export only reviewed manifests, metrics, model cards, checksums, and versioned artifacts.
- Treat pickle/joblib artifacts as executable code and load only packages created by the reviewed workflow.
- Delete the hosted runtime after approved outputs are exported.

## Approval states

- `candidate` — identified but not yet reviewed for a model run.
- `approved_for_preparation` — source, license, integrity process, labels, and adapter plan reviewed.
- `approved_for_training` — prepared schema and split manifest reviewed; fitting may begin in isolation.
- `approved_artifact` — output package independently verified and allowed for runtime loading.
- `rejected` — provenance, licensing, integrity, label, leakage, or compatibility requirements failed.

No code should translate `candidate` directly into `approved_artifact`.

## DNS tunnelling final-evaluation lock

The fixed DNS Threats Dataset v1 test split is the only fresh final source used by
the Issue #4 improvement workflow:

- filename: `test_combined_multiclass.csv.gz`;
- published MD5: `ce52df239c4245ffaa15c642b8b0b625`;
- locked SHA-256: `028fd97a4c498e8b6f22b93c2f804e4e0f3afe0c15ff5b3e71f9a12d0ddd4783`;
- schema: `domain,class`;
- label mapping: `0` to `BENIGN_DNS`, `2` to `DNS_TUNNEL`;
- label `1` (DGA) is excluded and counted, never relabelled; and
- candidate selection, calibration, and threshold derivation must not read this file.

This final source contains no timestamp, client, query type, or temporal sequence.
The adapter therefore marks those capabilities unavailable instead of inserting
invented observations. Results measure cross-source lexical generalization only and
must not be presented as live-network validation.
