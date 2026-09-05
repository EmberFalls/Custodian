# Custodian demo runbook

1. Confirm only approved captures exist in `data/demo/` and verify their recorded checksums and provenance.
2. Confirm `configs/models.yaml` leaves every unreviewed artifact with `trusted: false`.
3. Start the API on `127.0.0.1:8000` and the dashboard on `127.0.0.1:5173` using the README commands.
4. Check health and readiness before replay. An unavailable detector is an honest limitation, not a reason to enable a mock.
5. Select an approved capture, validate it, and run passive replay. Confirm packet/flow counts and parser limitations.
6. Explain that an alert is a calibrated assessment only when a trusted evaluated artifact is active; zero alerts does not prove safety.
7. Stop both processes with `Ctrl+C`. Do not expose either development server to the LAN.

Model training, dataset downloads, live interfaces, traffic generation, and network replay are not part of this runbook.
