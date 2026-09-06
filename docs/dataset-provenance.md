# Custodian dataset provenance

## Dataset

**CICIDS2017 / MachineLearningCSV**, published by the Canadian Institute for Cybersecurity at the University of New Brunswick.

Official source:
https://www.unb.ca/cic/datasets/ids-2017.html

The official dataset page states that the CSVs are labeled network flows generated with CICFlowMeter and asks users to cite the associated Sharafaldin, Lashkari and Ghorbani paper.

## Exact inputs used by Custodian

Custodian's approved Behaviour training path consumes exactly:

1. `Friday-WorkingHours-Morning.pcap_ISCX.csv`
2. `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
3. `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`

No PCAP files are required by this notebook.

## Provenance record for every run

Before training, record:

| Field | Value |
|---|---|
| Dataset source URL | official CICIDS2017 URL above |
| Dataset access date | fill in |
| Exact filenames | the three files above |
| File sizes | produced by the notebook |
| SHA-256 | produced by the notebook |
| Custodian Git commit | fill in from `git rev-parse HEAD` |
| Python version | printed by the notebook |
| Dependency versions | verified by the notebook |
| Notebook revision | fill in commit SHA |
| Output model version | e.g. `behaviour-xgb-colab-v1` |

Do not commit the CSVs, model binaries, calibration objects, or experiment-specific machine output.

## Citation

Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization*. 4th International Conference on Information Systems Security and Privacy (ICISSP).

## License / redistribution note

The official CIC page describes the dataset as publicly available for researchers and provides redistribution guidance on its dataset pages. Keep the dataset itself outside the Custodian repository and refer users to the official source rather than mirroring the CSVs.
