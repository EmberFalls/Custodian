# Custodian data governance

Datasets and captures are never trusted solely because of a filename or download location. Raw data stays outside Git. Each approved dataset requires a committed manifest containing its official origin, license, acquisition date, SHA-256 checksums, source schema, label meanings, allowed detector family, preprocessing version, known leakage risks, and approval state.

Training is deferred until the isolated VM is explicitly approved. The preferred initial input is official flow CSV data because it does not contain raw packet payloads. CSV content is still validated as untrusted data. PCAP/CAP files are parsed only in the offline VM with updated libraries and are never replayed onto a real or virtual network.

Label mappings must preserve source meaning. Broad labels cannot be narrowed into a more specific Custodian class. Exact IPs, domains, capture IDs, dataset row IDs, and attack-schedule timestamps are excluded as features unless a documented deployability review approves them. Splits are deterministic and group-aware; preprocessing and calibration are fit without held-out leakage.

Generated feature tables, models, calibrators, reports, and metrics remain ignored. An exported model package must contain checksums, feature order/version, dataset and split identities, class mapping, calibration, thresholds, dependency metadata, model card, and held-out evaluation reference. Custodian will show a detector as unavailable rather than load an incomplete, incompatible, corrupt, or unapproved package.
