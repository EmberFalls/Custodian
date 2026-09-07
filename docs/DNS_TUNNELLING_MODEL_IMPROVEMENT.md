# DNS tunnelling model improvement protocol

## Safety and trust status

This workflow runs only in a Google-hosted Colab runtime. It must not use a local
runtime, mount Google Drive, resolve any observed domain, replay or inject packets,
execute dataset contents, or import a dataset-provided model. All outputs remain
untrusted until a human reviews the provenance, metrics, source limitations, and
artifact hashes. `configs/models.yaml` must not be enabled automatically.

## Data roles

The three roles are deliberately separated:

1. **Development:** fifteen BCCC-CIC-Bell-DNS-2024 CSV scenarios. These alone feed
   grouped train, validation, calibration, and internal-test partitions.
2. **Diagnostic:** `benign_heavy_3.csv`, `heavy_audio.csv`, and `heavy_text.csv` from
   the BCCC source. This set may reveal weaknesses but may not be used to retune the
   completed candidate in the same run.
3. **Fresh final evaluation:** the immutable test split of DNS Threats Dataset v1,
   DOI `10.5281/zenodo.6508640`. It is locked before fitting and evaluated exactly
   once after candidate selection.

The DNSTunnel2026 archive, DOI `10.5281/zenodo.20137065`, was checksum-valid but
rejected. Its released CSVs contain source-engineered aggregates rather than the raw
DNS schema described on the record page. Custodian never loads the bundled binary
model and never uses those engineered columns.

## Candidate selection

The workflow compares Extra Trees, histogram gradient boosting, and Random Forest.
Every candidate uses balanced training weights. Calibration uses only the calibration
partition. The DNS-tunnel operating point uses only validation rows and applies the
same rule as runtime: the calibrated argmax must be `DNS_TUNNEL` and its score must
meet the selected threshold.

The predeclared validation and final-evaluation targets are:

- false-positive rate no greater than 1%;
- DNS-tunnel precision at least 90%; and
- DNS-tunnel recall at least 80%.

The winner is evaluated once on the internal test partition. The benign threshold in
the serialized mapping is a documented `0.0` non-alert sentinel because benign
verdicts return before Evidence Gate thresholding. It is not a claimed performance
threshold. The DNS-tunnel threshold is validation-derived.

## Independent evaluation boundary

`training/ctu_dns.py` downloads only the fixed Zenodo test split, verifies the
published MD5 and locked SHA-256, checks the exact two-column schema, and adapts only
raw domain strings through `custodian.features.dns.DNSFeatureExtractor`. DGA rows are
excluded and reported. Missing time, client, query type, and history are represented
as unavailable capabilities.

`evaluate_fresh_external_once` refuses to run if a final metrics file already exists
for the candidate package. It performs no fit, calibration, candidate selection, or
threshold change. Passing the numerical targets does not make the package trusted:
the benchmark lacks live temporal behavior and still requires human review and later
passive live-network validation.

## Expected review outputs

The candidate directory contains model and calibrator artifacts, feature/class/
threshold manifests, internal metrics, dataset provenance, diagnostic metrics, fresh
external metrics, review status, and `artifact_sha256.json`. The hash manifest is
verified before `joblib` deserialization. Only the reviewed archive and small reports
may be exported; raw or prepared datasets stay in the disposable Colab runtime.

## Hosted run outcome — 2026-09-06

This implementation was exercised in a Google-hosted free Colab runtime. The run
found and fixed two data-quality defects before final evaluation: the BCCC values
`not a dns flow` and `malformed-packet` are sentinels, not domain names. The reviewed
adapter rejected 134,020 such development rows and 53,837 diagnostic rows. The final
development table contained 286,368 DNS rows (99,559 benign and 186,809 tunnel).

Histogram gradient boosting was selected with an internally derived tunnel threshold
of `0.5168687443757688`. Results recorded by the hosted run were:

| Evaluation role | Rows | False-positive rate | Tunnel false-negative rate | Tunnel precision | Tunnel recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal test | 46,521 | 0.1511% | 0.1142% | 99.9216% | 99.8858% |
| BCCC diagnostic | 83,617 | 0.1903% | 0.1579% | 99.9463% | 99.8421% |
| Fresh DNS Threats v1 test | 237,631 | 0.0394% | 41.4368% | 90.7555% | 58.5632% |

The independent final split contained 236,072 benign and 1,559 tunnel rows after
383,072 DGA rows were excluded. Its fixed source SHA-256 was
`028fd97a4c498e8b6f22b93c2f804e4e0f3afe0c15ff5b3e71f9a12d0ddd4783`.

The candidate failed the predeclared 80% fresh-external recall target. Its review
status is `CANDIDATE_FAILED_PREDECLARED_EXTERNAL_TARGETS`, `trusted` is `false`, and
live-network validation is incomplete. The hosted archive SHA-256 was
`9c4dced9566361adbcecfd113b43fb04718d824e2bd4787f925035d0901efcc2`; the archive was
not downloaded to the local machine. These results must not be used to enable the DNS
model or to claim production accuracy.

## Round-two improvement protocol

Round two addresses the failed cross-dataset recall without treating the exposed
DNS Threats v1 test split as fresh evidence. The official
`train_combined_multiclass.csv.gz` split is added to development data, while its
published test split becomes a reused regression benchmark only. A different,
independent final evaluation is still required before the candidate can pass review.

The round-two model is intentionally restricted to lexical fields that the shared
`dns.v1` runtime extractor can obtain from a domain string in every approved source:
domain length, character entropy and composition ratios, label-shape statistics,
subdomain count, and the fixed bigram buckets. Query type, query frequency,
unique-domain ratio, history indicators, and feature-availability flags are excluded
from model input so the candidate cannot learn dataset-specific missingness.

Development uses BCCC DNS-EXF scenarios plus the official DNS Threats v1 training
split. Every tunnel row is retained. DNS Threats benign rows are deterministically
sampled at one in eight to keep the free Colab run bounded; the operating-point
precision calculation restores the negative class by a factor of eight. Model-fit
weights give equal total influence to every source-family and class combination.

Calibration and threshold selection use only grouped DNS Threats training-split
development rows. The round-two validation target is deliberately stricter: false-
positive rate no greater than 0.05%, tunnel precision at least 90%, and tunnel recall
at least 80%. No test-split row participates in fitting, calibration, model selection,
or threshold selection.

After fitting, the previously exposed DNS Threats v1 test split may be measured once
as a regression benchmark. Its report must say that it is not a fresh final
evaluation and cannot independently justify acceptance. The package status remains
`CANDIDATE_ROUND2_AWAITING_NEW_INDEPENDENT_EVALUATION`, `trusted: false`, and it must
not be enabled in `configs/models.yaml`.

## Round-two hosted outcome — 2026-09-07

The round-two pipeline was executed in a fresh Google-hosted Colab Free runtime.
Google Drive was not mounted, no domain was resolved, no traffic was replayed, and no
dataset or model artifact was downloaded to the local laptop. Histogram gradient
boosting was selected with a validation-derived threshold of
`0.8039048173317539`.

On the combined internal test partition, the candidate produced 99.1267% accuracy,
99.9791% tunnel precision, 96.9749% tunnel recall, and a 0.00816% benign false-
positive rate. On the CTU training-split validation partition, however, tunnel recall
was only 65.8268%; therefore the predeclared 80% validation-recall target was not met.

The already-exposed DNS Threats v1 test split was used only as a non-fresh regression
benchmark. It produced:

- 99.7109% accuracy;
- 98.2301% tunnel precision;
- 56.9596% tunnel recall;
- 0.00678% false-positive rate;
- 43.0404% false-negative rate;
- 75.8581% average precision; and
- 99.5022% ROC-AUC.

Relative to round one, ranking quality, precision, and false-positive rate improved,
but recall decreased from 58.5632% to 56.9596%. The candidate therefore did not meet
the acceptance target and must not replace the current reviewed state. Its archive
SHA-256 is `51e1925492e10befeb24a54cf88fbe22d85fee64cfa30c3f68f57ebfb6d47a65`.
The archive remains only in the disposable hosted runtime.

Two follow-up experiments were explicitly rejected. A richer hashed n-gram candidate
met validation recall but fell to 10.8403% recall on the reused benchmark, indicating
source-specific overfitting; its extra extractor fields were removed from the local
code. A CTU-only fit reached 63.7588% reused-benchmark recall but only 71.7172%
precision. Neither experimental result was packaged for integration, trusted, or
enabled. The next legitimate step is a new training source containing additional raw
DNS-tunnelling families followed by a different, untouched independent evaluation.
