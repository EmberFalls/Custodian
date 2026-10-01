import { useEffect, useRef, useState } from "react";

/**
 * Animates a number from previous value (or 0 on initial mount) to target `to`
 * over `duration` ms with smooth ease-out cubic progression.
 */
export function useCountUp(to: number, duration = 1200, enabled = true): number {
  const [value, setValue] = useState(0);
  const prevValueRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      setValue(to);
      prevValueRef.current = to;
      return;
    }

    const startVal = prevValueRef.current;
    const endVal = to;
    if (startVal === endVal && value === endVal) return;

    const startTime = performance.now();
    const delta = endVal - startVal;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic: starts with energy, smoothly decelerates
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startVal + delta * eased);
      setValue(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        prevValueRef.current = endVal;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [to, duration, enabled]);

  return value;
}
