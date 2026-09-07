# Data policy

Raw research datasets, processed training tables, downloaded captures, and
generated training manifests are intentionally excluded from Git. A teammate
does **not** need any training dataset to run inference with the distributed
Behaviour model.

## Layout

```text
data/
├── raw/          # downloaded source datasets; ignored
├── processed/    # generated feature tables; ignored
├── manifests/    # local preparation/training manifests; ignored
└── demo/         # authorized local replay captures; ignored
```

## Behaviour-model training data

The distributed Behaviour model was trained from the CICIDS2017
`MachineLearningCSV` flow exports using these source files:

- `Friday-WorkingHours-Morning.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`

Source labels map to Custodian classes as follows:

| CICIDS2017 label | Custodian class |
| --- | --- |
| `BENIGN` | `BENIGN` |
| `DDoS` | `DDOS` |
| `PortScan` | `RECON` |
| `Bot` | `BOT_OR_C2_LIKE` |

These CSV files are large research inputs and are never committed to this
repository. They are required only for approved retraining work in the isolated
data-handling workflow described in `docs/data-governance.md`.
