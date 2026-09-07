# Custodian — Complete Project, Implementation, Data and Model Dossier

**Document status:** Repository-derived implementation record  
**Snapshot date:** 7 September 2026  
**Repository:** <https://github.com/EmberFalls/Custodian>  
**Product name:** Custodian  
**Application type:** Local-first, passive network-security monitoring and explainable threat-detection MVP

> This document records what exists in the current local Custodian codebase and model packages. It does not turn an internal candidate into a production-approved model. Every numerical result below comes from a stored model report or is clearly marked as derived from its stored confusion matrix. No result is fabricated.

---

## 1. Executive summary

Custodian is a passive network-analysis system designed to help an operator understand suspicious behaviour visible in network metadata. It can read an authorised packet capture, reconstruct bidirectional flows, extract reproducible features, run compatible trained models, apply evidence and confidence checks, create explainable alerts, persist results locally, and display the activity in a browser dashboard.

The system is intentionally local-first:

- the API binds to `127.0.0.1`;
- the frontend is served locally;
- PCAP replay means reading a file, not retransmitting its packets;
- no active scan, exploit, mitigation, injection or traffic generation exists;
- TLS and QUIC payloads are not decrypted;
- dataset domains are treated as inert strings and are never resolved or contacted; and
- raw datasets were processed in disposable Google-hosted Colab runtimes, not on the presentation laptop.

The current local showcase contains four trained candidate model packages:

| Detector | Selected model | Classes | Local artifact | Current status |
| --- | --- | --- | --- | --- |
| Behaviour | XGBoost `XGBClassifier` | `BENIGN`, `DDOS`, `RECON`, `BOT_OR_C2_LIKE` | `model_artifacts/behaviour-colab-v1` | Trained and locally loadable for the MVP; internal target met; external evaluation incomplete |
| DNS tunnelling | `HistGradientBoostingClassifier` | `BENIGN_DNS`, `DNS_TUNNEL` | `model_artifacts/dns-tunnelling-colab-v1` | Trained and locally loadable for the MVP; external recall target not met |
| Encrypted session / TLS-QUIC metadata | `HistGradientBoostingClassifier` | `BENIGN_ENCRYPTED`, `MALICIOUS_ENCRYPTED_SESSION` | `model_artifacts/tls-quic-colab-v1` | Trained and locally loadable for the MVP; strong internal DoH result; external evaluation incomplete |
| DNS DGA | `HistGradientBoostingClassifier` | `BENIGN` and `DGA` | `model_artifacts/dns-dga-drift26dsn-hgb-v1` | Trained and locally loadable for the MVP; held-out-family recall is weak; external evaluation incomplete |

The `configs/models.demo.local.yaml` override currently enables the four available packages for a localhost-only demonstration. Its `trusted: true` value means only that the local operator has permitted deserialisation for the demo; it is not a production or independent-validation claim. Repository defaults remain conservative.

---

## 2. Problem being solved

Network defenders face large volumes of packet and flow data, while encrypted traffic prevents payload inspection and raw alerts often lack context. Custodian addresses this by combining:

1. passive metadata collection;
2. canonical bidirectional flow reconstruction;
3. bounded temporal state;
4. shared training/runtime feature extraction;
5. specialised detector families;
6. confidence calibration and operating thresholds;
7. capability-aware evidence gating;
8. conservative multi-model fusion;
9. explainable, persistent alert records; and
10. a local dashboard designed for a live demonstration.

The intended operator question is not merely “did a model return a high number?” It is:

> What was observed, which detector evaluated it, what evidence was available, what evidence was missing, how confident was the detector, and why did Custodian accept, downgrade or suppress the alert?

---

## 3. Scope and safety boundaries

### 3.1 Implemented scope

- Authorised `.cap`, `.pcap` and `.pcapng` discovery and validation.
- File identity using SHA-256, size bounds and confined-path checks.
- Incremental passive capture parsing.
- Ethernet, Linux cooked and raw-IP input support.
- IPv4 and IPv6 parsing.
- TCP, UDP, ICMP, visible DNS, TLS and QUIC metadata extraction.
- Canonical bidirectional flow reconstruction.
- Initiator-relative direction and flow close reasons.
- Bounded temporal windows and state.
- Shared, versioned feature schemas.
- Behaviour, DNS and TLS/QUIC detector wrappers.
- Model-package compatibility, integrity and trust checks.
- Confidence calibration and class-specific thresholds.
- Evidence availability and missing-evidence representation.
- Severity scoring, deduplication and alert lifecycle.
- Local SQLite persistence and restart recovery.
- Replay start, pause, resume, stop, reset and forward/backward seek.
- JSON and CSV exports with provenance and spreadsheet-injection escaping.
- Versioned FastAPI HTTP API and WebSocket event streams.
- Authentication for the local demonstration UI.
- Responsive dashboard for replay, telemetry, flows, alerts, detector readiness and performance.

### 3.2 Not implemented or not activated

- Real passive capture from a physical network interface is not currently activated.
- Zeek, NetFlow/IPFIX and sFlow adapters are declared but unavailable.
- DNS DGA has an integrated local MVP candidate, but its held-out-family performance is below a production threshold.
- Independent external evaluation is incomplete for Behaviour and TLS/QUIC.
- DNS-tunnelling fresh-external recall did not meet the declared 80% target.
- Production authentication, remote deployment, multi-tenant access and public hosting are not claimed.
- Active scanning, attack generation, mitigation, packet transmission and payload execution are out of scope.
- TLS/QUIC payload decryption is out of scope.

### 3.3 Passive replay guarantee

Custodian's “replay” is deterministic file processing. It reads stored frames and advances application time. There is no code path that injects those frames into a network interface. A capture may contain bytes that once represented malicious activity, but Custodian does not execute or transmit those bytes.

---

## 4. System architecture

```text
Authorised capture file
        |
        v
Capture validation and SHA-256 identity
        |
        v
Incremental packet parser
        |
        +--> visible DNS metadata
        +--> visible TLS/QUIC metadata
        +--> TCP/UDP/ICMP metadata
        |
        v
Canonical bidirectional flows
        |
        v
Bounded temporal state and ObservationFrame
        |
        v
Shared versioned feature extraction
        |
        v
Capability and distribution-support checks
        |
        +--> Behaviour detector
        +--> DNS detector
        +--> TLS/QUIC metadata detector
        |
        v
Calibration + operating threshold + evidence gate
        |
        v
Conservative fusion, severity and deduplication
        |
        +--> SQLite persistence
        +--> event stream
        +--> metrics
        |
        v
FastAPI HTTP/WebSocket API
        |
        v
React/Vite local dashboard
```

### 4.1 Major implementation areas

| Area | Important paths | Responsibility |
| --- | --- | --- |
| Contracts | `src/custodian/core`, `src/custodian/contracts` | Stable enums and schemas for packets, flows, features, verdicts, alerts and events |
| Capture ingestion | `src/custodian/ingest`, `src/custodian/ingestion` | Validation and incremental read-only capture ingestion |
| Parsing | `src/custodian/parsing` | Packet, DNS and TLS/QUIC metadata parsing |
| Flows | `src/custodian/flow` | Canonical keys, flow state and bounded flow management |
| Temporal state | `src/custodian/state` | Rolling host/domain observations and temporal snapshots |
| Features | `src/custodian/features` | Shared Behaviour, DNS and TLS/QUIC feature extraction |
| Models | `src/custodian/models` | Artifact integrity, compatibility, calibration and batch inference |
| Detection | `src/custodian/detection` | Per-family detector wrappers and unavailable-detector behaviour |
| Evidence | `src/custodian/evidence` | Evidence quality, capability requirements and acceptance decisions |
| Fusion | `src/custodian/fusion` | Conservative combination of detector verdicts |
| Alerts | `src/custodian/alerts` | Alert construction, severity and repetition deduplication |
| Persistence | `src/custodian/storage` | Local SQLite storage, lifecycle and recovery |
| Runtime | `src/custodian/runtime` | Pipeline orchestration, replay, checkpoints and benchmarks |
| Telemetry | `src/custodian/telemetry` | Throughput, packet/flow counts, latency, CPU and memory metrics |
| API | `src/custodian/api` | Local FastAPI HTTP and WebSocket interface |
| Frontend | `frontend/src` | Landing page, login, dashboard, replay controls, charts and inspectors |
| Training | `training`, `notebooks` | Hosted-Colab preparation, splitting, fitting, calibration, evaluation and export |

---

## 5. Runtime data and decision flow

1. The operator places an authorised capture in `data/demo/`.
2. The API lists only files confined to the approved directory.
3. Capture validation verifies extension, format, size, path and identity.
4. The replay engine reads packets incrementally.
5. The parser retains metadata needed by the prototype and does not retain raw payloads for execution.
6. Packets update canonical bidirectional flows.
7. Flow and packet observations update bounded temporal state.
8. Each applicable feature extractor creates a versioned `FeatureVector` plus an availability map.
9. A detector runs only when a compatible local model package is enabled, trusted by the operator and loadable.
10. The model produces raw and calibrated probabilities.
11. The applicable class threshold and evidence gate determine whether evidence is strong enough to accept an alert.
12. Weak or missing evidence can produce `UNKNOWN_SUSPICIOUS` or `INSUFFICIENT_EVIDENCE` instead of an unjustified named threat.
13. Accepted decisions pass through severity and deduplication.
14. Alerts, flows, events and metrics are persisted and streamed to the frontend.

---

## 6. Common machine-learning methodology

### 6.1 Training environment

The reviewed workflows use a disposable Google-hosted Colab runtime:

- Google Drive is not mounted.
- The laptop filesystem is not mounted.
- Data is downloaded into a Colab-owned workspace.
- Dataset contents are not executed.
- Domains are never resolved, pinged or enriched.
- PCAP traffic is never replayed onto a network.
- Training uses metadata CSV/Parquet data where possible.
- Only model packages, metrics, manifests and hashes are exported.
- The Colab runtime is discarded after export.

The locally compatible serialization versions are pinned in `constraints-demo.txt`:

| Library | Version |
| --- | --- |
| joblib | 1.5.2 |
| NumPy | 2.2.6 |
| scikit-learn | 1.7.2 for the locally verified showcase runtime |
| SciPy | 1.15.3 |
| XGBoost | 3.0.2 |

The hosted workflow requirements are recorded separately in `training/requirements-colab.txt`.

### 6.2 Shared features

The application does not substitute arbitrary dataset columns at runtime. Dataset adapters translate reviewed source fields into the same versioned features produced by `src/custodian/features`.

Rules include:

- unavailable information is marked unavailable, not filled with invented evidence;
- labels, source identifiers and row IDs are never predictive features;
- training/runtime schema compatibility is checked before inference;
- candidates may use only a declared subset of runtime-reproducible fields; and
- preprocessing is packaged with the estimator where required.

### 6.3 Four-role split

Training workflows separate four roles:

- **Train:** fits estimator parameters.
- **Validation:** compares candidates and chooses operating thresholds.
- **Calibration:** fits held-out probability calibration.
- **Test:** measures the selected, fixed candidate once after selection.

Group identities remain in one role. The nominal group split is approximately 70% train, 10% validation, 10% calibration and 10% test. Row percentages differ when groups have different sizes.

### 6.4 Calibration and thresholds

- Behaviour uses a held-out one-vs-rest sigmoid calibrator followed by probability normalisation.
- DNS tunnelling and TLS/QUIC use held-out sigmoid calibration through scikit-learn.
- Operating points are selected on validation data, never on the internal test data.
- The runtime decision requires the calibrated positive class and the stored positive-class threshold.
- A benign threshold of `0.0` is a package-completeness sentinel; benign results return before alert thresholding.

---

## 7. Model 1 — Behaviour threat classifier

### 7.1 Purpose and claim boundary

This model classifies completed network-flow metadata into:

- `BENIGN`;
- `DDOS`;
- `RECON`; and
- `BOT_OR_C2_LIKE`.

`BOT_OR_C2_LIKE` is a conservative mapping of the CICIDS2017 `Bot` label. It is not proof of validated C2 beaconing. Exfiltration is not a trained output of this package.

### 7.2 Dataset

**Dataset:** CICIDS2017 MachineLearningCSV  
**Publisher:** Canadian Institute for Cybersecurity, University of New Brunswick  
**Official page:** <https://www.unb.ca/cic/datasets/ids-2017.html>  
**Downloaded mirror revision:** Hugging Face `San0160/CICIDS-2017`, revision `acc006479c77c0d1904fd5549a1b32658d9f7ab3`  
**Raw PCAP downloaded:** No

Files used:

| File | Relevant source labels | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | BENIGN, Bot | 58,316,725 | `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000` |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | BENIGN, PortScan | 76,906,168 | `ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b` |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | BENIGN, DDoS | 77,123,859 | `6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee` |

Label mapping:

| Source label | Custodian label |
| --- | --- |
| `BENIGN` | `BENIGN` |
| `DDoS` | `DDOS` |
| `PortScan` | `RECON` |
| `Bot` | `BOT_OR_C2_LIKE` |

Cleaning outcome:

| Item | Count |
| --- | ---: |
| Invalid core rows removed | 47 |
| Exact duplicate feature rows removed | 220,529 |
| Conflicting feature rows removed | 18,208 |
| Final BENIGN rows | 333,332 |
| Final DDOS rows | 127,987 |
| Final RECON rows | 1,913 |
| Final BOT_OR_C2_LIKE rows | 1,229 |
| Total final rows | 464,461 |

### 7.3 Features

The model uses 14 shared flow features:

1. flow duration in seconds;
2. outbound packets;
3. inbound packets;
4. total packet count;
5. outbound payload bytes;
6. inbound payload bytes;
7. total payload bytes;
8. mean payload packet size;
9. payload packet-size variance;
10. mean inter-arrival time;
11. inter-arrival variance;
12. directional payload ratio;
13. flow packets per second; and
14. flow payload bytes per second.

Destination port, ambiguous TCP flags, unavailable protocol, CIC-only global packet statistics and fabricated temporal host fields were excluded.

### 7.4 Estimator and exact parameters

**Estimator:** `xgboost.XGBClassifier`

```text
objective        = multi:softprob
num_class        = 4
n_estimators     = 300
max_depth        = 5
learning_rate    = 0.08
subsample        = 0.9
colsample_bytree = 0.9
tree_method      = hist
reg_lambda       = 2.0
random_state     = 42
n_jobs           = 2 in the recorded Colab artifact
eval_metric      = mlogloss
```

Class balancing used inverse-frequency sample weights on training rows only:

| Class | Recorded weight |
| --- | ---: |
| BENIGN | 0.3490376810 |
| DDOS | 0.9025247727 |
| RECON | 59.7653621068 |
| BOT_OR_C2_LIKE | 97.6096176822 |

### 7.5 Split

Groups are contiguous 512-row blocks within each original source file, retained before cleaning. Groups do not overlap across roles, but they are provenance proxies rather than verified host/session groups; therefore the evaluation is not described as leakage-free.

| Role | Groups | Rows | BENIGN | DDOS | RECON | BOT/C2-like |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 959 | 326,797 | 234,070 | 90,523 | 1,367 | 837 |
| Validation | 137 | 47,497 | 34,579 | 12,621 | 179 | 118 |
| Calibration | 137 | 43,232 | 31,100 | 11,811 | 191 | 130 |
| Final internal test | 137 | 46,935 | 33,583 | 13,032 | 176 | 144 |

**Split seed:** `1818`  
**Seed rule:** first group partition containing every class in every role; no performance-based seed search.

### 7.6 Thresholds

| Class | Stored threshold |
| --- | ---: |
| BENIGN | 0.0003347964651196156 |
| DDOS | 0.00003307814490175072 |
| RECON | 0.006659895421161771 |
| BOT_OR_C2_LIKE | 0.8332234261921887 |

Thresholds were derived from validation probabilities with a declared minimum class precision target of 0.80. Final test labels were not used for threshold selection.

### 7.7 Final calibrated internal-test results

| Metric | Result |
| --- | ---: |
| Rows | 46,935 |
| Accuracy | 99.7656% |
| Macro precision | 92.2829% |
| Macro recall | 97.0389% |
| Macro F1 | 94.3357% |
| Weighted precision | 99.7925% |
| Weighted recall | 99.7656% |
| Weighted F1 | 99.7750% |
| Multiclass Brier score | 0.00344995 |
| Expected calibration error, 10 bins | 0.0711% |

Per-class results:

| Class | Precision | Recall | F1 | Support | One-vs-rest FPR* |
| --- | ---: | ---: | ---: | ---: | ---: |
| BENIGN | 99.8600% | 99.8124% | 99.8362% | 33,583 | 0.3520% |
| DDOS | 99.9539% | 99.7698% | 99.8618% | 13,032 | 0.0177% |
| RECON | 99.4253% | 98.2955% | 98.8571% | 176 | 0.00214% |
| BOT_OR_C2_LIKE | 69.8925% | 90.2778% | 78.7879% | 144 | 0.1197% |

`*` FPR values are derived directly from the stored final-test confusion matrix.

Confusion matrix, rows = true and columns = predicted, class order `BENIGN`, `DDOS`, `RECON`, `BOT_OR_C2_LIKE`:

```text
[[33520,     6,   1,  56],
 [   30, 13002,   0,   0],
 [    3,     0, 173,   0],
 [   14,     0,   0, 130]]
```

Overall threat-versus-benign values derived from that matrix:

- benign flows incorrectly classified as an attack: **0.1876%**;
- attack flows incorrectly classified as benign: **0.3520%**.

### 7.8 Review status and limitations

**Stored status:** `CANDIDATE_INTERNAL_TARGET_MET_EXTERNAL_EVALUATION_REQUIRED`  
**Allowed claim:** CICIDS2017 flow-classification candidate  
**Not allowed:** validated C2 detection, exfiltration detection or live-network accuracy

The internal results are strong, but CICIDS2017 flow rows lack the original IPs, timestamps and verified session identities required for a stronger independent deployment claim. Partial runtime-flow snapshots may also differ from completed CICFlowMeter rows.

---

## 8. Model 2 — TLS/QUIC metadata encrypted-session classifier

### 8.1 Purpose and claim boundary

This binary model evaluates runtime-reproducible encrypted-flow metadata:

- `BENIGN_ENCRYPTED`;
- `MALICIOUS_ENCRYPTED_SESSION`.

Its training source represents DoH tunnelling. Therefore the precise allowed claim is an experimental DoH-tunnel encrypted-session candidate, not universal malicious TLS/QUIC detection.

### 8.2 Dataset

**Dataset:** BCCC-CIRA-CIC-DoHBrw-2020  
**Publisher:** Behaviour-Centric Cybersecurity Center, York University  
**BCCC page:** <https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/>  
**Selected file:** `BCCC-CIRA-CIC-DoHBrw-2020.csv`  
**File size:** 216,120,294 bytes  
**SHA-256:** `ef625bb2a4bbd2e280fe2d2fdd6f6805bae3397bc75ffd653505108e1f5e45d7`

Preparation outcome:

| Item | Count |
| --- | ---: |
| Input rows | 499,106 |
| Duplicate feature rows removed | 22,041 |
| Conflicting feature rows removed | 0 |
| Invalid numeric rows | 0 |
| Prepared rows | 477,065 |
| BENIGN_ENCRYPTED | 233,515 |
| MALICIOUS_ENCRYPTED_SESSION | 243,550 |
| Groups | 975 |

The source is balanced using SMOTE and is not a natural-traffic prevalence sample. Custodian did not perform further synthetic oversampling.

### 8.3 Features

Nine numeric metadata features plus their nine explicit availability indicators are used:

1. flow duration;
2. total bytes;
3. mean packet size;
4. packet-size variance;
5. bytes A-to-B;
6. bytes B-to-A;
7. directional byte ratio;
8. byte rate A-to-B; and
9. byte rate B-to-A.

Source-only labels and identifiers, incompatible packet-time statistics and response-time fields absent from runtime were excluded.

### 8.4 Candidate models and exact parameters

Two candidates were trained and calibrated. Histogram gradient boosting was selected using validation-only operating-point performance.

**Selected HGB:**

```text
learning_rate     = 0.08
max_iter          = 300
max_leaf_nodes    = 31
l2_regularization = 1.0
random_state      = 42
preprocessing     = median imputation, keep_empty_features=True
training weights  = balanced sample weights
```

**Compared Extra Trees:**

```text
n_estimators    = 250
min_samples_leaf = 2
n_jobs          = -1
random_state    = 42
preprocessing   = median imputation, keep_empty_features=True
training weights = balanced sample weights
```

### 8.5 Split

| Role | Groups | Rows |
| --- | ---: | ---: |
| Train | 681 | 333,276 |
| Validation | 98 | 47,939 |
| Calibration | 98 | 47,939 |
| Internal test | 98 | 47,911 |

**Split seed:** `3240`  
**Group overlap:** none  
**Grouping limitation:** contiguous row blocks are proxies, not verified host/session groups.

### 8.6 Operating target and threshold

Validation targets:

- maximum false-positive rate: 5%;
- minimum malicious precision: 80%;
- minimum malicious recall: 80%.

Stored thresholds:

| Class | Threshold |
| --- | ---: |
| BENIGN_ENCRYPTED | 0.0 non-alert sentinel |
| MALICIOUS_ENCRYPTED_SESSION | 0.5676423194264345 |

### 8.7 Validation result for selected HGB

| Metric | Result |
| --- | ---: |
| Accuracy | 99.8498% |
| Malicious precision | 99.8814% |
| Malicious recall | 99.8243% |
| False-positive rate | 0.1236% |
| False-negative rate | 0.1757% |
| Average precision | 99.9978% |
| ROC-AUC | 99.9976% |
| Brier score | 0.00128550 |
| Log loss | 0.00526753 |

Validation confusion matrix:

```text
[[23437,    29],
 [   43, 24430]]
```

### 8.8 Final internal-test result

| Metric | Result |
| --- | ---: |
| Rows | 47,911 |
| Accuracy | 99.8038% |
| Malicious precision | 99.8812% |
| Malicious recall | 99.7342% |
| Malicious F1 | 99.8076% |
| False-positive rate | 0.1236% |
| False-negative rate | 0.2658% |
| Average precision | 99.9951% |
| ROC-AUC | 99.9942% |
| Brier score | 0.00145986 |
| Log loss | 0.00611073 |

Confusion matrix, rows = true `BENIGN_ENCRYPTED`, `MALICIOUS_ENCRYPTED_SESSION`:

```text
[[23430,    29],
 [   65, 24387]]
```

### 8.9 Review status and limitations

**Stored status:** `CANDIDATE_INTERNAL_EVALUATION_COMPLETE_EXTERNAL_EVALUATION_REQUIRED`  
**Validation target met:** Yes  
**Independent external evaluation:** No

The result is strong on the internal BCCC DoH split, but the dataset does not cover every malicious encrypted session and lacks several TLS/QUIC handshake, host and timestamp fields. The dashboard must not present this result as universal TLS/QUIC malware accuracy.

---

## 9. Model 3 — DNS tunnelling classifier

### 9.1 Purpose

The DNS tunnelling model classifies visible DNS query-name lexical metadata as:

- `BENIGN_DNS`;
- `DNS_TUNNEL`.

It does not resolve domains and does not inspect or execute reconstructed payload content.

### 9.2 Datasets and their roles

#### BCCC-CIC-Bell-DNS-2024 development data

**Publisher:** BCCC, York University  
**Official page:** <https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/malicious-dns-and-attacks-bccc-cic-bell-dns-2024/>  
**Subset:** BCCC-CIC-Bell-DNS-EXF  
**Files used:** 15 benign/light/heavy DNS scenario CSV files

After rejecting invalid sentinel values such as `not a dns flow` and `malformed-packet`:

| Class | Rows |
| --- | ---: |
| BENIGN_DNS | 99,559 |
| DNS_TUNNEL | 186,809 |
| Total | 286,368 |

#### DNS Threats Dataset v1 development and benchmark data

**DOI:** <https://doi.org/10.5281/zenodo.6508640>

The round-two workflow used only the official training split for fitting, calibration and selection:

- file: `train_combined_multiclass.csv.gz`;
- published MD5: `c30a49c6f362e0c2dffe3881504a6825`;
- verified SHA-256: `9bc7c1e53d67c2b5ad9352a45bc415107521da10e96572d0ed5e4586b80e4de9`;
- input fields: `domain,class`;
- DGA rows excluded rather than relabelled;
- benign rows deterministically sampled one in eight for a bounded Colab run;
- all tunnel rows retained;
- resulting rows: 118,217 benign and 6,441 tunnel.

The official test split was not used to fit, calibrate, select a model or choose the round-two threshold. Because it had already been examined during round one, its later round-two result is labelled a reused regression benchmark, not fresh independent evidence.

### 9.3 Combined round-two preparation

| Item | Count |
| --- | ---: |
| Prepared rows | 411,026 |
| BENIGN_DNS | 217,776 |
| DNS_TUNNEL | 193,250 |
| Unique groups | 114,770 |

Fit weights gave equal total influence to each source-family/class stratum. A factor of eight corrected the validation precision calculation for the deterministically sampled CTU benign class.

### 9.4 Features

The selected package uses 16 universally observable lexical features:

- character entropy;
- digit ratio;
- domain length;
- hyphen ratio;
- letter ratio;
- mean label length;
- repeated-character ratio;
- subdomain count; and
- eight deterministic bigram buckets.

Query type, query frequency, unique-domain ratio, timestamps, source availability flags and temporal history were excluded so the model could not learn source-specific missingness. Median imputation is packaged with the estimator.

### 9.5 Candidates and exact parameters

Three candidates were compared:

**Selected HGB:**

```text
learning_rate     = 0.08
max_iter          = 300
max_leaf_nodes    = 31
l2_regularization = 1.0
random_state      = 42
preprocessing     = median imputation, keep_empty_features=True
```

**Extra Trees:**

```text
n_estimators     = 300
min_samples_leaf = 2
n_jobs           = -1
random_state     = 42
```

**Random Forest:**

```text
n_estimators     = 300
min_samples_leaf = 2
n_jobs           = -1
random_state     = 42
```

### 9.6 Split

| Role | Groups | Rows |
| --- | ---: | ---: |
| Train | 80,339 | 280,972 |
| Validation | 11,477 | 38,911 |
| Calibration | 11,477 | 56,791 |
| Internal test | 11,477 | 34,352 |

**Split seed:** `7077`  
**Group allocation:** approximately 70/10/10/10 by group count.  
**Selection domain:** CTU official training-split validation partition only.

### 9.7 Declared operating targets

- maximum false-positive rate: 0.05%;
- minimum precision: 90%;
- minimum recall: 80%.

### 9.8 Round-two selected-candidate validation

The selected HGB validation operating point was:

| Metric | Result |
| --- | ---: |
| Threshold | 0.8039048173317539 |
| Precision | 91.2664% |
| Recall | 65.8268% |
| False-positive rate | 0.04227% |
| False-negative rate | 34.1732% |
| Average precision | 92.4693% |
| ROC-AUC | 99.2924% |
| Meets all targets | No — recall below 80% |

### 9.9 Combined internal-test result

| Metric | Result |
| --- | ---: |
| Rows | 34,352 |
| Accuracy | 99.1267% |
| Tunnel precision | 99.9791% |
| Tunnel recall | 96.9749% |
| Tunnel F1 | 98.4541% |
| Benign false-positive rate | 0.00816% |
| Tunnel false-negative rate | 3.0251% |

Confusion matrix:

```text
[[24499,    2],
 [  298, 9553]]
```

This strong combined internal figure must be read with the weaker CTU-only validation result because BCCC source-family rows are much easier for the candidate.

### 9.10 Fresh round-one external result

The first model round selected HGB with threshold `0.5168687443757688`. The then-fresh DNS Threats v1 test split contained 236,072 benign and 1,559 tunnel rows after 383,072 DGA rows were excluded.

| Metric | Result |
| --- | ---: |
| Rows | 237,631 |
| Precision | 90.7555% |
| Recall | 58.5632% |
| False-positive rate | 0.0394% |
| False-negative rate | 41.4368% |
| Passed 80% recall target | No |

The round-one archive remained in the disposable hosted runtime and was not approved.

### 9.11 Round-two reused benchmark result

At the round-two validation-derived operating point:

| Metric | Result |
| --- | ---: |
| Accuracy | 99.7109% |
| Tunnel precision | 98.2301% |
| Tunnel recall | 56.9596% |
| False-positive rate | 0.00678% |
| False-negative rate | 43.0404% |
| Average precision | 75.8581% |
| ROC-AUC | 99.5022% |

This benchmark was no longer fresh and could not independently approve the candidate.

### 9.12 Current MVP demonstration operating point

For the localhost demonstration, the stored local package uses a lower `DNS_TUNNEL` threshold of `0.05`. This is explicitly a demo operating point, not the original validation-selected acceptance threshold.

| Metric on reused benchmark | Result |
| --- | ---: |
| Threshold | 0.05 |
| Accuracy | 99.6983% |
| Tunnel precision | 89.2724% |
| Tunnel recall | 61.3855% |
| Tunnel F1 | 72.7480% |
| False-positive rate | 0.04871% |
| False-negative rate | 38.6145% |
| Passed 80% recall target | No |

Confusion matrix:

```text
[[235957,    115],
 [   602,    957]]
```

### 9.13 Review status

**Stored local status:** `TRAINED_LOCAL_MVP_DEMO_CANDIDATE`  
**Allowed use:** local passive demonstration and continued development  
**Fresh independent target passed:** No  
**Production approved:** No

The model is real and trained; it is not a hard-coded rule. Its principal weakness is cross-source tunnel recall. The correct demonstration statement is that Custodian can operationalise and explain a trained DNS-tunnelling candidate, while further source diversity and untouched external evaluation are required to improve and validate recall.

---

## 10. DNS DGA model — trained MVP candidate

### 10.1 What currently exists

The local code now implements a corrected DGA preparation and HGB training path based on the useful parts of PR #11:

- expected source files: `T17_benign.parquet` and `T17_dga.parquet`;
- source labels mapped to `BENIGN` and `DGA`;
- DGA family names retained for audit;
- lexical DNS features derived through Custodian-compatible formulas;
- whole-DGA-family grouped train/validation/calibration/test roles; and
- HGB with held-out sigmoid calibration.

The integration also allows DNS tunnelling and DGA to run as separate DNS detector variants, declares the DGA positive-threshold decision policy in the artifact manifest, applies that same policy at runtime, permits a validated runtime feature superset, verifies artifact hashes before deserialization, and includes a synthetic train-export-load-infer contract test.

Proposed HGB parameters in that PR:

```text
max_iter       = 300
learning_rate  = 0.05
max_leaf_nodes = 31
random_state   = 42
preprocessing  = median imputation
```

### 10.2 Training data, split and measured result

The model was trained in a disposable hosted Colab runtime from the pinned Hugging Face dataset revision `3b31077020cd1c013d0a75cad51042a2327c4521` of `snsec-net/dga-detection-drift26dsn`. The 2017 raw tables were downloaded and SHA-256 verified inside Colab. The prepared sample retained 299,999 benign domains and 215,088 DGA domains spanning 58 DGA families. Dataset domains were never resolved or contacted, and no payload or packet replay occurred.

DGA families were kept wholly within one role. The selected split seed was `7876`: training used 361,455 rows with 40 DGA families; validation used 50,989 rows with 6 held-out families; calibration used 51,648 rows with 6 held-out families; and internal test used 50,995 rows with 6 held-out families.

The exported DGA threshold is `0.5739183019306983`. At that validation-derived operating point:

| Metric | Validation | Internal held-out-family test |
| --- | ---: | ---: |
| Accuracy | 79.3681% | 62.2630% |
| DGA precision | 80.0012% | 62.3721% |
| DGA recall | 65.7073% | 25.0983% |
| False-positive rate | 11.2639% | 10.9239% |
| False-negative rate | 34.2927% | 74.9017% |
| ROC AUC | 0.869876 | 0.703735 |
| Average precision | 0.848991 | 0.583084 |

The weaker internal test result is important: that role contains DGA families excluded from training, so it exposes limited family generalisation. The package is a genuine trained MVP candidate and is locally integrated, but it is not production approved and has not received independent external evaluation.

### 10.3 Remaining DGA work

1. Improve held-out-family recall with richer shared features and more representative temporal/family sampling.
2. Evaluate against a new untouched external DGA source.
3. Recalibrate and select an operating point appropriate to the demonstration without relabelling or fabricating metrics.
4. Preserve the current artifact as the reproducible baseline while evaluating improved candidates.

---

## 11. Model artifact and runtime integration

Each generic candidate package contains:

```text
model.joblib or model.json
calibrator.joblib
feature_schema.json
classes.json or class_mapping.json
thresholds.json
metrics.json
manifest.json
dataset_provenance.json where applicable
review_status.json
artifact_sha256.json
```

Runtime loading checks:

- artifact directory exists;
- required JSON metadata is valid;
- classes map to supported Custodian `ThreatClass` values;
- thresholds are complete, finite and between zero and one;
- model and calibrator class order matches metadata;
- feature family and schema version match runtime vectors;
- selected feature columns are compatible;
- hashes match for the reviewed packages; and
- the detector is enabled and explicitly trusted by local configuration.

The runtime does not silently substitute rules when a model is missing. It reports the detector as unavailable or degraded.

---

## 12. Evidence-aware alerting

A model score alone is insufficient for a named alert. Custodian also evaluates:

- which metadata was actually visible;
- the capture/source capability profile;
- required and missing feature evidence;
- whether observations are within supported feature ranges;
- calibrated confidence;
- the stored class threshold;
- repetition and temporal context; and
- agreement or conflict between detector families.

Possible outcomes include:

| Outcome | Meaning |
| --- | --- |
| Named accepted threat | Model, threshold and evidence requirements support the class |
| `UNKNOWN_SUSPICIOUS` | Activity is suspicious but a precise supported class is not justified |
| `INSUFFICIENT_EVIDENCE` | Required evidence is absent or capability is too weak |
| No alert | Benign result, threshold not reached or evidence gate suppresses it |

Alert records include source/destination, threat class, severity, calibrated confidence, decision, evidence, missing evidence, model version, schema version, timestamps, occurrence count and lifecycle status.

---

## 13. Backend, API and persistence

### 13.1 Backend

- Framework: FastAPI.
- Bind address: `127.0.0.1`.
- Default port: `8000`.
- Persistence: local SQLite.
- API prefix: `/api/v1`.
- Interactive documentation: `/docs` and `/redoc` while the backend runs.

### 13.2 Main API groups

- authentication: login, current user, logout and demo credentials;
- health and readiness;
- capture listing and validation;
- replay status, start, pause, resume, stop, seek and reset;
- telemetry and measured metrics;
- alert listing, inspection, acknowledgement and closure;
- detector/model readiness;
- flow and host timeline queries;
- diagnostics;
- resumable event polling;
- bounded JSON/CSV export; and
- WebSocket telemetry, alerts, metrics and application events.

The complete request/response contract is in `docs/api.md`.

### 13.3 Persistence

SQLite stores bounded operational state including alerts, lifecycle changes, flow summaries, application events, capture/checkpoint information and restart recovery data. Queries are parameterised and retention is bounded.

---

## 14. Frontend and operator experience

The React/Vite frontend communicates with the real local API rather than embedding detector decisions in the UI.

The operator can see:

- global monitor state and readiness;
- source type and replay progress;
- packets, inspected bytes, packet rate, flows, active flows and throughput;
- a bounded traffic timeline;
- inspection-pipeline stage status;
- detector availability and model metadata;
- filterable and sortable alerts;
- threat class, severity, source, destination and confidence;
- alert evidence and missing-evidence detail;
- host behaviour leading up to an alert;
- replay start/pause/resume/stop/reset controls;
- forward and backward seek with visible rebuilding state;
- measured CPU, memory and latency information; and
- explicit degraded/unavailable states instead of fake healthy status.

The current visual system uses graphite/deep-green surfaces, emerald primary states, cyan telemetry, amber warnings and red critical states.

---

## 15. Replay and live-network status

### 15.1 Demonstration input

The implemented input is passive file replay. Supported capture extensions are `.cap`, `.pcap` and `.pcapng`, subject to content validation. CSV training datasets cannot be started from the replay UI.

### 15.2 Real live monitoring

Real interface capture is a future opt-in adapter. It would require:

1. an explicitly selected authorised interface;
2. a read-only capture backend such as Npcap/libpcap;
3. capture filters and least-privilege operation;
4. bounded queues and drop counters;
5. reuse of the existing packet, flow, temporal, feature and detector pipeline;
6. no promiscuous mode unless explicitly approved and legally authorised;
7. no packet transmission path;
8. a separate privacy and retention review; and
9. disconnected/lab validation before use on a real network.

It is not correct to claim that current file replay is already live-interface monitoring.

---

## 16. Current local showcase configuration

The ignored local override currently points to:

```yaml
models:
  behaviour:
    enabled: true
    trusted: true
    schema_version: behaviour.v1
    artifact_path: model_artifacts/behaviour-colab-v1
  dns:
    enabled: true
    trusted: true
    schema_version: dns.v1
    artifact_path: model_artifacts/dns-tunnelling-colab-v1
  tls_quic:
    enabled: true
    trusted: true
    schema_version: tls_quic.v1
    artifact_path: model_artifacts/tls-quic-colab-v1
```

This configuration is intentionally not the repository default and should not be committed as a universal trust decision.

---

## 17. Running the complete local MVP

### Backend

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.local.yaml'
$env:LOKY_MAX_CPU_COUNT = '4'
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian\frontend'
& 'E:\Node\npm.cmd' run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>.

The model-compatible local virtual environment should be installed using `constraints-demo.txt`. Do not use an arbitrary scikit-learn/joblib version to load the packages.

---

## 18. Verification and testing

The repository includes unit and integration coverage for:

- schemas and enums;
- capture validation;
- parser and flow reconstruction;
- DNS, Behaviour and TLS/QUIC feature extraction;
- training safety gates;
- grouped split isolation;
- model integrity and compatibility;
- calibration/operating points;
- evidence and fusion;
- alert severity and deduplication;
- persistence and export;
- replay control and seeking;
- API routes and API documentation;
- Colab workflow constraints; and
- real Behaviour artifact loading when explicitly approved.

Standard verification commands:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m pytest -q
& 'E:\Python\python.exe' -m ruff check src tests training
Set-Location frontend
& 'E:\Node\npm.cmd' run build
```

---

## 19. Honest demonstration claims

### Safe claims

- Custodian is passive and local-first.
- It performs real packet parsing, flow reconstruction and shared feature extraction.
- It uses real trained candidate models, not hard-coded threat rules.
- Behaviour, DNS tunnelling and encrypted-session candidate packages are locally integrated for the MVP.
- Model outputs are calibrated and evaluated against stored thresholds and evidence.
- Alerts contain evidence, confidence, model/schema provenance and lifecycle state.
- The UI is connected to a real local API and measured runtime telemetry.
- PCAP replay never injects traffic.
- Training data remained in disposable hosted environments.

### Claims that must not be made

- “All models are production ready.”
- “DNS tunnelling achieved 80% independent recall.”
- “TLS/QUIC detects every malicious encrypted connection.”
- “Bot traffic proves validated C2 attribution.”
- “DGA is production ready” or “DGA generalises to unseen families” based on the current weak held-out-family result.
- “The current application already monitors a physical interface live.”
- “Internal test accuracy guarantees live-network accuracy.”
- “The system provides 100% security or detection.”

---

## 20. Known limitations and next priorities

1. Improve DGA held-out-family recall and perform untouched external evaluation.
2. Improve DNS-tunnel cross-source recall with additional raw-domain tunnelling families.
3. Use a new untouched external DNS-tunnelling evaluation source.
4. Externally evaluate the Behaviour classifier on a compatible independent flow dataset.
5. Externally evaluate the TLS/QUIC candidate beyond the BCCC DoH distribution.
6. Add controlled passive live-interface ingestion in an isolated lab.
7. Measure laptop throughput, packet drops and latency on the final presentation hardware.
8. Complete dependency/security audit and release hardening before any non-demo deployment.

---

## 21. Repository sources of truth

| Subject | Source |
| --- | --- |
| Governing implementation plan | `docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md` |
| Architecture | `docs/architecture.md` |
| API | `docs/api.md` |
| Dataset governance | `docs/data-governance.md` |
| Dataset provenance rules | `docs/dataset-provenance.md` |
| Colab workflow | `docs/colab-training.md` |
| DNS improvement history | `docs/DNS_TUNNELLING_MODEL_IMPROVEMENT.md` |
| Behaviour training implementation | `training/train_behaviour.py` |
| DNS candidate implementation | `training/train_dns_candidates.py` |
| TLS/QUIC candidate implementation | `training/train_tls_quic_candidates.py` |
| Behaviour model record | `model_artifacts/behaviour-colab-v1` |
| DNS-tunnelling model record | `model_artifacts/dns-tunnelling-colab-v1` |
| TLS/QUIC model record | `model_artifacts/tls-quic-colab-v1` |
| DNS-DGA model record | `model_artifacts/dns-dga-drift26dsn-hgb-v1` |
| Default model policy | `configs/models.yaml` |
| Local demo template | `configs/models.demo.example.yaml` |
| Local compatible versions | `constraints-demo.txt` |

---

## 22. Final project state

Custodian is a functional passive PCAP-analysis MVP with a real backend, real frontend, persistent alert workflow, evidence-aware decisions, deterministic replay controls and four locally integrated trained candidate packages. It is suitable for a transparent localhost demonstration of the architecture and model operationalisation.

It is not yet a production network defence platform. DGA held-out-family robustness and real interface capture remain incomplete, and independent external evaluation is still required for important model claims. Those limitations are visible by design rather than concealed by mocks or fabricated results.
