# Custodian architecture

Custodian uses a passive streaming pipeline:

```text
authorized capture -> validation -> metadata parser -> canonical flows
                   -> bounded temporal state -> shared versioned features
                   -> observation/capability gate -> approved model runtime
                   -> evidence/fusion -> persistence/events -> local API/dashboard
```

The parser exposes only observable metadata. Flow and temporal state are bounded. Training, evaluation, replay, and any later passive live mode import the same feature package. Detector families cannot run when their required capabilities or trusted artifacts are missing. The API is a local interface over application services; the frontend consumes typed API/event contracts rather than detector internals.

Offline replay is file pacing, not network replay. It has no transmission path. Optional live capture is a later, separate, opt-in phase and must feed the same downstream contracts without adding active behavior.
