# Google Colab training issue: detailed setup and contribution guide

## Goal of the issue

The Google Colab issue should produce a reproducible, auditable training environment shared by Custodian's model contributors. It is infrastructure for later model issues; it must not silently train or approve a model by itself.

Colab keeps compute away from the developer's local Windows host, but it is not an absolute security guarantee. Dataset files are still untrusted data. Contributors must avoid local runtimes, Google Drive over-sharing, network traffic generation, payload execution, and unreviewed serialized model files.

Official service links:

- Google Colab: <https://colab.research.google.com/>
- Colab FAQ: <https://research.google.com/colaboratory/faq.html>
- Hugging Face DGA dataset selected for DNS/DGA work: <https://huggingface.co/datasets/harpomaxx/dga-detection>
- ExtraHop DGA dataset for optional external comparison: <https://github.com/ExtraHop/DGA-Detection-Training-Dataset>
- CIC-IDS2017 for Behaviour-model work: <https://www.unb.ca/cic/datasets/ids-2017.html>
- CIC-Bell-DNS-EXF-2021 for later DNS-tunnelling work: <https://www.unb.ca/cic/datasets/dns-exf-2021.html>
- CipherSpectrum TLS 1.3 dataset: <https://cgi.cse.unsw.edu.au/~cspectrum/>
- CESNET DataZoo TLS/QUIC datasets: <https://cesnet.github.io/cesnet-datazoo/datasets_overview/>

Dataset links are references, not blanket approval. Every model issue must select only the data needed for that family and document its license, revision, checksum, schema, label meaning, and leakage risks.

## Recommended GitHub issue

### Title

```text
Create a safe, reproducible Google Colab training workflow
```

### Suggested labels

```text
training, google-colab, security, documentation
```

### Dependencies

- Shared feature contracts in `src/custodian/features/`.
- Training safety gate in `training/safety.py`.
- Prepared-table contract in `training/prepare.py`.
- Common trainer in `training/train_common.py`.
- Dataset-specific model issues for Behaviour, DNS, and TLS/QUIC.

### Scope

The contributor should create:

- `notebooks/custodian_training_colab.ipynb`;
- `docs/colab-training.md` for human instructions;
- a pinned Colab requirements/constraints file if the existing project extras are insufficient;
- dataset-manifest examples containing provenance and checksums but no dataset rows;
- a smoke-test mode using a tiny, synthetic structural fixture clearly marked as a pipeline test, not training evidence; and
- automated checks that the notebook does not use a local runtime or start network replay.

The issue must not commit raw datasets, processed datasets, secrets, Colab credentials, Google Drive tokens, model binaries, or fabricated metrics.

## Important current repository constraint

The current common trainer does not accept arbitrary raw Hugging Face rows. It expects a prepared Parquet table whose columns include:

- `label`;
- `group_id`;
- `source_name`;
- `family`;
- `schema_version`;
- `entity_id`;
- `window_id`;
- `feature__<name>` columns; and
- matching `available__<name>` columns.

For DNS training, every row must identify `family = dns` and `schema_version = dns.v1`. The raw Hugging Face DGA dataset supplies `domain`, `label`, and `class`; it does not already contain Custodian's shared `dns.v1` feature vector.

Therefore, the DNS/DGA model issue must implement a reviewed adapter that converts each domain string through the shared DNS feature extraction implementation and then uses `training.prepare.feature_rows`. Training directly on ad-hoc notebook features would violate the train/runtime parity requirement.

## Notebook structure

The notebook should be divided into explicit, independently rerunnable sections.

### 1. Safety notice and acknowledgement

The first cell should state:

- This notebook processes datasets as untrusted data.
- Do not select **Connect to local runtime**.
- Do not resolve, visit, ping, or send DNS queries to listed domains.
- Do not replay PCAP traffic.
- Do not execute extracted payloads or companion scripts.
- Do not place credentials in notebook cells.
- Delete the Colab runtime after exporting approved outputs.

The repository safety gate requires two deliberate signals before model fitting:

1. Set `CUSTODIAN_ISOLATED_TRAINING=YES` inside the Colab runtime.
2. Call the training function with `isolation_acknowledged=True`.

These signals record acknowledgement; they do not prove isolation.

### 2. Runtime verification

The notebook should print and record:

- Python version;
- operating system/runtime information;
- CPU/GPU/RAM availability;
- package versions;
- repository commit SHA;
- whether a local runtime is detected; and
- current UTC timestamp.

GPU is not required for the existing Random Forest trainer. Selecting a GPU should not be presented as improving accuracy.

### 3. Obtain the repository

Clone the public Custodian repository into the temporary Colab filesystem and checkout a specific branch or commit. Do not execute code from an unreviewed pull request without inspecting it first.

The notebook should expose a `CUSTODIAN_COMMIT` variable and record it in the final manifest. Runs against an unspecified moving `main` branch are not reproducible.

### 4. Install pinned dependencies

Install only project-declared/pinned dependencies. Print resolved versions after installation. Dependency installation requires internet access; dataset processing and training should begin only after required downloads have completed.

The notebook must not disable Colab security controls, browser protections, TLS certificate validation, package signature/checksum verification, or Python warnings merely to make installation succeed.

### 5. Select one dataset and model family

Each notebook run should select one detector family and one declared dataset manifest. Do not concatenate unrelated sources automatically.

For the initial DNS/DGA run:

| Field | Required value |
| --- | --- |
| Primary source | `harpomaxx/dga-detection` |
| Source URL | `https://huggingface.co/datasets/harpomaxx/dga-detection` |
| Published license | `CC-BY-2.0` |
| Runtime task | Binary `BENIGN` vs `DGA_LIKE` |
| Family labels | Retained for grouping and evaluation, not asserted as runtime attribution |
| Prohibited action | Resolving or visiting any domain in the data |

The dataset card reports 2,918,496 total domains, including 1,003,161 benign domains and 1,915,335 DGA domains from 51 DGA families. The displayed training split contains approximately 2.04 million rows. The notebook must calculate and report the counts it actually receives rather than copying these numbers into results.

### 6. Record provenance and integrity

Before transformation, capture:

- canonical dataset URL and repository/dataset revision;
- access date in UTC;
- published license and required attribution;
- downloaded filenames;
- byte size;
- SHA-256 for every downloaded data file;
- original columns and dtypes;
- row counts;
- missing-value counts;
- duplicate-domain counts;
- exact source-label meanings; and
- any discrepancy with the dataset card.

The manifest must be exportable as JSON. It may be committed only if it contains no private paths, tokens, or dataset content.

### 7. Validate and normalize raw data

For DNS/DGA domain strings:

- treat every value as inert text;
- do not render values as clickable URLs;
- do not perform HTTP, WHOIS, DNS, or reputation lookups;
- reject null, empty, non-string, or structurally invalid rows according to a documented policy;
- normalize case and trailing dots consistently;
- document treatment of internationalized domain names;
- preserve the original label and source in audit columns;
- detect conflicting labels for identical normalized domains; and
- avoid using the source name or family label as a predictive feature.

Do not silently rewrite labels or convert a broad malicious-domain label into a DGA-family claim.

### 8. Shared feature extraction

The notebook must import Custodian feature code from the checked-out repository. It must not contain a second independent implementation of production features.

The adapter should produce `FeatureVector` objects with:

- family `dns`;
- schema `dns.v1`;
- identical values and availability flags to runtime extraction;
- deterministic `entity_id` and `window_id`; and
- no raw row ID, family name, domain source, or label embedded as a feature.

If the current DNS extractor requires flow fields unavailable in a domain-only dataset, the contributor must stop and document the mismatch. They may propose a versioned lexical-DGA schema, but must not pretend missing flow evidence exists.

### 9. Leakage-resistant splitting

At minimum, produce four roles:

- training;
- validation for threshold selection;
- calibration;
- final held-out testing.

Required protections:

- normalize and deduplicate domains before splitting;
- keep identical registrable domains in a single split;
- keep related/generated samples grouped where identifiers permit;
- prevent preprocessing from fitting on held-out rows; and
- use deterministic seeds recorded in the manifest.

For DGA, report two evaluation protocols:

1. **Known-family evaluation:** stratified, grouped splits where each evaluated family may also appear during training.
2. **Unseen-family evaluation:** hold out complete DGA families from model fitting, threshold selection, and calibration.

Random-row accuracy must not be described as unseen-family performance.

### 10. Fit, calibrate, and evaluate

Use the repository trainer unless a model issue explicitly approves a change. The current shared trainer uses a balanced Random Forest, median imputation, sigmoid calibration, validation-derived class thresholds, and a separate test split.

Required metrics include:

- class counts for every split;
- precision, recall, and F1 per binary class;
- macro and weighted F1;
- confusion matrix;
- benign false-positive rate;
- calibration metric/curve;
- threshold-selection method;
- per-family DGA recall;
- known-family result;
- held-out-family result; and
- peak RAM and elapsed training time.

Do not fabricate or manually edit metrics. A failed or incomplete run should be reported as such.

### 11. Export an artifact package

The exported package must include:

- estimator;
- calibrator;
- class order/mapping;
- class thresholds;
- exact ordered feature schema;
- model family and version;
- dataset manifest identity;
- split manifest identity;
- repository commit;
- dependency versions;
- evaluation reference;
- model card;
- checksums for package files; and
- limitations, including whether family attribution is unsupported.

Do not mark an artifact trusted inside Colab. Trust approval occurs after independent review and compatibility testing.

Because common Python serialization formats can execute code while loading, only export artifacts created by the reviewed notebook. Never load a pickle/joblib artifact supplied by an unknown third party.

### 12. Export and destroy

Export only:

- notebook with outputs reviewed for secrets;
- dataset and split manifests;
- metrics and plots;
- model card;
- versioned artifact package; and
- package checksums.

Do not export raw dataset copies unless separately required and approved. Do not commit large artifacts to ordinary Git. Use approved release/artifact storage or Git LFS if the team formally adopts it.

Finally, disconnect and delete the Colab runtime. Colab isolation protects the local laptop only if a local runtime and unsafe local mounts are not used.

## Suggested contributor workflow

1. Assign the GitHub issue and comment with the intended scope.
2. Create a branch such as `feature/colab-training-workflow`.
3. Implement the notebook and documentation without adding dataset files.
4. Run the notebook from a fresh hosted Colab runtime.
5. Save outputs that demonstrate dependency versions, schemas, checksums, split counts, and smoke-test success.
6. Scan the notebook for tokens, user paths, and hidden outputs.
7. Open a pull request linked to the issue.
8. Request review from both an ML reviewer and a security/data-governance reviewer.
9. Do not close the issue until a second person reproduces the smoke-test workflow.

## Pull-request evidence

The PR should contain:

- a link to the issue;
- notebook and documentation files;
- exact repository commit used in the Colab demonstration;
- package/version output;
- structural fixture results;
- evidence that no dataset/model binary is committed;
- a dataset manifest example;
- a list of outbound accesses performed during setup/download;
- known limitations; and
- confirmation that no local runtime was used.

## Acceptance criteria

- [ ] A fresh hosted Colab runtime can execute the setup and smoke-test sections in order.
- [ ] The workflow checks out a recorded Custodian commit.
- [ ] Dependencies and versions are reproducible.
- [ ] Dataset provenance, license, revision, size, and checksums are recorded.
- [ ] Raw source rows pass through a reviewed adapter and shared Custodian feature code.
- [ ] Prepared tables match the `training.prepare` contract.
- [ ] Training remains blocked without both explicit isolation acknowledgements.
- [ ] Train, validation, calibration, and test roles are separate and deterministic.
- [ ] DGA evaluation includes a complete-family holdout.
- [ ] No domain is visited or resolved.
- [ ] No PCAP is replayed and no traffic is generated.
- [ ] No secrets, datasets, model binaries, or invented results are committed.
- [ ] Artifact trust remains false until independent review.
- [ ] A second contributor can reproduce the smoke test.

## Out of scope

- Connecting Colab to the developer's local runtime.
- Live-interface capture testing.
- Active scanning or DNS probing.
- Generating DGA domains with malware code.
- Executing malware or extracted payloads.
- Training all model families in one undifferentiated notebook run.
- Automatically setting `trusted: true` in `configs/models.yaml`.
- Claiming family attribution from a binary detector.

