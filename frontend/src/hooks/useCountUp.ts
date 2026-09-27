import { useEffect, useRef, useState } from "react";

/**
 * Animates a number from 0 (or `from`) to `to` over `duration` ms.
 * Only starts when `enabled` is true (tie to useInView for scroll-trigger).
 */
export function useCountUp(to: number, duration = 900, enabled = true, from = 0): number {
  const [value, setValue] = useState(from);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const startTime = performance.now();
    const delta = to - from;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(from + delta * eased));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [to, from, duration, enabled]);

  return value;
}
