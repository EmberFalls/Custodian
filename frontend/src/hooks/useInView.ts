import { useEffect, useRef, useState } from "react";

/**
 * Returns a [ref, isVisible] tuple.
 * Attach `ref` to any DOM element; `isVisible` becomes true once
 * that element scrolls into the viewport (and stays true by default).
 */
export function useInView(options?: IntersectionObserverInit): [React.RefObject<HTMLElement | null>, boolean] {
  const ref = useRef<HTMLElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          // Once visible, no need to keep observing
          observer.unobserve(el);
        }
      },
      { threshold: 0.12, ...options }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return [ref, isVisible];
}
