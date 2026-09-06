interface CustodianShieldIconProps {
  size?: number;
}

export function CustodianShieldIcon({ size = 32 }: CustodianShieldIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="shield-grad" x1="16" y1="2" x2="16" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00f0ff" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>
        <linearGradient id="inner-grad" x1="16" y1="8" x2="16" y2="26" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.05" />
        </linearGradient>
        <filter id="shield-glow">
          <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Shield outline */}
      <path
        d="M16 2L4 7.5V15.5C4 21.8 9.3 27.6 16 30C22.7 27.6 28 21.8 28 15.5V7.5L16 2Z"
        fill="url(#inner-grad)"
        stroke="url(#shield-grad)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        filter="url(#shield-glow)"
      />

      {/* Network node center */}
      <circle cx="16" cy="16" r="2.2" fill="#00f0ff" opacity="0.9" />

      {/* Network spokes */}
      <line x1="16" y1="13.8" x2="16" y2="10" stroke="#00f0ff" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      <line x1="18.2" y1="16" x2="22" y2="16" stroke="#00f0ff" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      <line x1="16" y1="18.2" x2="16" y2="22" stroke="#00f0ff" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
      <line x1="13.8" y1="16" x2="10" y2="16" stroke="#00f0ff" strokeWidth="1" strokeLinecap="round" opacity="0.5" />

      {/* Diagonal spokes */}
      <line x1="17.55" y1="14.45" x2="19.8" y2="12.2" stroke="#6366f1" strokeWidth="0.8" strokeLinecap="round" opacity="0.5" />
      <line x1="14.45" y1="14.45" x2="12.2" y2="12.2" stroke="#6366f1" strokeWidth="0.8" strokeLinecap="round" opacity="0.5" />

      {/* Endpoint nodes */}
      <circle cx="16" cy="9.5" r="1.2" fill="#00f0ff" opacity="0.75" />
      <circle cx="22" cy="16" r="1.2" fill="#00f0ff" opacity="0.6" />
      <circle cx="16" cy="22.5" r="1.2" fill="#6366f1" opacity="0.55" />
      <circle cx="10" cy="16" r="1.2" fill="#6366f1" opacity="0.55" />
      <circle cx="19.8" cy="12.2" r="0.9" fill="#6366f1" opacity="0.45" />
      <circle cx="12.2" cy="12.2" r="0.9" fill="#6366f1" opacity="0.45" />

      {/* Passive eye (scan arc at top right of shield) */}
      <path d="M22 9 Q24 10.5 24 12" stroke="#00f0ff" strokeWidth="1" strokeLinecap="round" opacity="0.4" fill="none" />
    </svg>
  );
}
