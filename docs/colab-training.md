# Custodian hosted Google Colab workflow

## Purpose and scope

`notebooks/custodian_training_colab.ipynb` establishes the shared, reproducible environment used by later model-training issues. Issue #1 ends after environment verification, repository tests, and export of an environment manifest. It does not download a dataset, prepare training rows, open the training safety gate, fit a model, or approve an artifact.

Model ownership remains separate:

- Issue #2: Behaviour model and CICIDS2017 adapter/run.
- Issue #3: DNS DGA model and domain-to-`dns.v1` shared-feature adapter.
- Issue #4: DNS-tunnelling model.
- Issue #5: TLS/QUIC metadata model.

This separation prevents one notebook from silently combining incompatible datasets or feature schemas.

## Safety boundary

Use only a Google-hosted Colab runtime. Do not select **Connect to local runtime**. The notebook contains marker and acknowledgement checks that reject obvious local-runtime use, but software checks cannot prove isolation.

The common notebook:

- does not mount Google Drive;
- does not accept dataset uploads;
- does not open a packet-capture interface;
- does not replay or transmit packets;
- does not resolve or visit observed domains;
- does not set `CUSTODIAN_ISOLATED_TRAINING`;
- does not fit a model;
- works only inside `/content/custodian-workspace`; and
- deletes only that exact owned workspace after explicit confirmation.

Dependency installation and cloning require outbound internet from Google's hosted runtime. They do not connect Colab to the user's local network.

## Before opening the notebook

1. Review the commit containing the Colab workflow.
2. Copy its complete 40-character Git SHA from GitHub.
3. Open a new hosted Colab runtime.
4. Confirm that the runtime is not connected to a local machine or private VPN.
5. Do not upload datasets, credentials, SSH keys, cloud service keys, or private files.

## Running the notebook

Open `notebooks/custodian_training_colab.ipynb` in Google Colab and run cells in order.

In the first configuration cell, set:

```python
CUSTODIAN_COMMIT = "the-full-reviewed-40-character-commit-sha"
HOSTED_COLAB_ACKNOWLEDGEMENT = "I AM USING A HOSTED GOOGLE COLAB RUNTIME"
```

The notebook then:

1. verifies hosted Colab markers and the acknowledgement;
2. validates that the revision is an immutable full Git SHA;
3. creates the exact owned directory `/content/custodian-workspace`;
4. clones the public repository and checks out the requested commit in detached mode;
5. verifies that `HEAD` equals the requested commit;
6. installs exact direct pins from `training/requirements-colab.txt`;
7. installs the checked-out Custodian package with `--no-deps` so the editable install cannot alter those pins;
8. records the final resolved `pip freeze` environment;
9. imports shared contracts and feature code;
10. runs Colab workflow, training-safety, schema, and shared-feature unit tests;
11. writes `colab-environment-manifest.json` with commit, Python, platform, timestamp, and dependency information; and
12. allows the user to download that small manifest.

No model metric is produced because no model is trained.

## Why a full commit SHA is required

Branches such as `main` move. A notebook that clones the latest branch can run different code on different days while presenting itself as reproducible. The shared workflow therefore rejects branch names and abbreviated revisions.

The environment manifest records the resolved commit. A later model run must copy this identity into its training manifest.

## Dependency policy

`training/requirements-colab.txt` pins the direct runtime and test dependencies used by the workflow. The notebook installs Custodian afterward with `--no-deps`, then records the complete resolved environment using `pip freeze`.

When pins need updating:

1. update them in a dedicated reviewed pull request;
2. run all tests in a fresh hosted Colab runtime;
3. review release notes and security implications;
4. update the expected manifest evidence; and
5. never bypass platform or certificate protections to force installation.

## Handoff to model-specific issues

A model-specific notebook or extension may proceed only after it defines:

- one detector family and schema version;
- official dataset source and license;
- dataset revision and file SHA-256 values;
- source label meanings and allowed Custodian mappings;
- a reviewed source adapter;
- identical shared training/runtime feature extraction;
- deterministic grouped train, validation, calibration, and test roles;
- leakage and domain-shift limitations;
- artifact package format; and
- independent trust/compatibility review.

Only the model-specific fitting cell may deliberately set:

```python
os.environ["CUSTODIAN_ISOLATED_TRAINING"] = "YES"
```

and pass the explicit training acknowledgement. The shared setup notebook must not do so.

## Cleanup

After downloading the environment manifest, set the final cell's confirmation to exactly:

```python
CLEANUP_CONFIRMATION = "DELETE CUSTODIAN COLAB WORKSPACE"
```

The cleanup helper verifies the owned path before removing `/content/custodian-workspace`. Finally, use **Runtime → Disconnect and delete runtime** in Colab.

The cleanup cell refuses to delete `/content`, a home directory, or any path other than Custodian's dedicated workspace.

## Verification on the repository

Run locally without training:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m pytest -q tests\unit\test_colab_workflow.py tests\unit\test_training_safety.py
& 'E:\Python\python.exe' -m ruff check training tests
```

## Definition of done for Issue #1

- [ ] Notebook is valid, output-free notebook JSON.
- [ ] Hosted-runtime acknowledgement and marker checks run before filesystem changes.
- [ ] A full reviewed Git SHA is mandatory.
- [ ] Checked-out `HEAD` is verified.
- [ ] Direct dependencies are pinned and the final resolved environment is recorded.
- [ ] Custodian installation cannot silently replace pins.
- [ ] No dataset input or model fitting exists in the common notebook.
- [ ] No local runtime, Drive mount, capture, replay, scanning, or traffic injection is used.
- [ ] Shared contracts/features import from the checked-out repository.
- [ ] Relevant structural tests pass.
- [ ] The environment manifest downloads successfully.
- [ ] Cleanup is confined to one dedicated path and requires explicit confirmation.
- [ ] A second contributor reproduces the workflow from a fresh hosted runtime.
