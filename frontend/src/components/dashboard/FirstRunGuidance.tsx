import { useState } from "react";

interface FirstRunGuidanceProps {
  connected: boolean;
  hasRunHistory: boolean;
  hasReadyCapture: boolean;
}

export function FirstRunGuidance({ connected, hasRunHistory, hasReadyCapture }: FirstRunGuidanceProps) {
  const [collapsed, setCollapsed] = useState(false);

  // If already running or has history and user dismissed, keep out of the way
  if (hasRunHistory && hasReadyCapture) return null;

  return (
    <aside className={`dash-onboarding ${collapsed ? "is-collapsed" : ""}`} aria-label="First-run operational guidance">
      <div className="dash-onboarding__header">
        <div className="dash-onboarding__title font-mono">
          <span className="dash-onboarding__pill">QUICKSTART</span>
          <span>RUNTIME GUIDANCE & TRUTHFULNESS NOTICE</span>
        </div>
        <button
          className="dash-onboarding__toggle font-mono"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand guidance" : "Collapse guidance"}
        >
          {collapsed ? "+ Expand Guidance" : "— Dismiss"}
        </button>
      </div>

      {!collapsed ? (
        <div className="dash-onboarding__grid">
          <div className="dash-onboarding__step">
            <div className="dash-onboarding__num font-mono">01</div>
            <div>
              <strong>Backend Status: {connected ? "Connected" : "Reconnecting..."}</strong>
              <p>Custodian is a local-only passive observation engine listening on 127.0.0.1:8000.</p>
            </div>
          </div>

          <div className="dash-onboarding__step">
            <div className="dash-onboarding__num font-mono">02</div>
            <div>
              <strong>Authorized Local PCAPs</strong>
              <p>Only verified <code>.cap</code>, <code>.pcap</code>, or <code>.pcapng</code> files placed in <code>data/demo/</code> are accepted.</p>
            </div>
          </div>

          <div className="dash-onboarding__step">
            <div className="dash-onboarding__num font-mono">03</div>
            <div>
              <strong>Passive Validation First</strong>
              <p>Select an approved capture and click <em>Validate</em> to inspect checksums and datalink layers prior to replay.</p>
            </div>
          </div>

          <div className="dash-onboarding__step">
            <div className="dash-onboarding__num font-mono">04</div>
            <div>
              <strong>PACED vs FAST Mode</strong>
              <p><em>PACED</em> preserves capture timestamps (1×–10×); <em>FAST</em> processes packets as quickly as local CPU allows.</p>
            </div>
          </div>

          <div className="dash-onboarding__step dash-onboarding__step--warn">
            <div className="dash-onboarding__num font-mono">!</div>
            <div>
              <strong>Truthfulness Contract</strong>
              <p>Zero alerts does not prove traffic is benign. Incomplete or unapproved detector models will remain explicitly unavailable.</p>
            </div>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
