# Demo captures

This directory is intentionally empty after a fresh clone. Packet captures are
not required to install Custodian or load the distributed Behaviour model.

Place only an authorized, locally obtained `.pcap`, `.pcapng`, or compatible
`.cap` file here before using replay controls. Custodian validates the capture
and reads it passively; it does not transmit or inject captured traffic.

Do not commit research-dataset captures, downloaded PCAP archives, or captures
containing data that cannot be redistributed. The repository includes tools for
creating clearly marked, offline-only mock fixtures when an integration demo
needs one:

```powershell
& '.\.venv\Scripts\python.exe' tools/create_mock_recon_demo.py --output data/demo/mock_recon_demo.pcap
```

The generated file remains ignored and is not a benchmark, a real intrusion
capture, or evidence of real-world detection performance.
