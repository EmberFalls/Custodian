import { useEffect, useRef } from "react";

/**
 * Zeabur-Exact 3D Topographic Binary Wave Canvas
 *
 * - Renders a dense, high-resolution monospace grid of '0' and '1' characters.
 * - Simulates a continuous 3D mathematical wave surface with multi-octave harmonic interference.
 * - Topographic contour lines and crests light up in vibrant Zeabur purple/lavender/white.
 * - Active wave crests continuously mutate and flip digits in real-time, matching Zeabur's live behavior.
 * - Mouse cursor interaction causes radial elevation deflection and localized digit excitation.
 * - Device-pixel-ratio (DPR) aware for crisp rendering on high-DPI displays.
 */
export function BinaryWaveCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    // Grid geometry
    const FONT_SIZE = 11;       // px font size
    const CELL_WIDTH = 9.5;     // px per column (condensed monospace)
    const CELL_HEIGHT = 12.5;   // px per row
    const FONT_SPEC = `500 ${FONT_SIZE}px "IBM Plex Mono", "Geist Mono", monospace`;

    let width = 0;
    let height = 0;
    let cols = 0;
    let rows = 0;
    let dpr = 1;

    // Grid data
    interface Cell {
      val: "0" | "1";
      lastFlip: number;
    }

    let grid: Cell[][] = [];
    const mouse = { x: -9999, y: -9999, targetX: -9999, targetY: -9999 };

    const initGrid = (newCols: number, newRows: number) => {
      const newGrid: Cell[][] = [];
      for (let r = 0; r < newRows; r++) {
        const row: Cell[] = [];
        for (let c = 0; c < newCols; c++) {
          const existing = grid[r]?.[c];
          row.push(
            existing ?? {
              val: Math.random() > 0.5 ? "1" : "0",
              lastFlip: 0,
            }
          );
        }
        newGrid.push(row);
      }
      grid = newGrid;
      cols = newCols;
      rows = newRows;
    };

    const handleResize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const newCols = Math.ceil(width / CELL_WIDTH) + 2;
      const newRows = Math.ceil(height / CELL_HEIGHT) + 2;
      initGrid(newCols, newRows);
    };

    handleResize();

    let animationFrameId = 0;
    let startTime = performance.now();

    const render = (now: number) => {
      const t = (now - startTime) * 0.001; // seconds

      // Smooth mouse interpolation
      mouse.x += (mouse.targetX - mouse.x) * 0.12;
      mouse.y += (mouse.targetY - mouse.y) * 0.12;

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      ctx.font = FONT_SPEC;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const hoverRadius = 140;
      const hoverRadiusSq = hoverRadius * hoverRadius;

      // Render cells and update dynamic digit flow
      for (let r = 0; r < rows; r++) {
        const py = r * CELL_HEIGHT + CELL_HEIGHT * 0.5;
        // Normalize y in range [-1, 1]
        const ny = (r / rows) * 2 - 1;

        for (let c = 0; c < cols; c++) {
          const px = c * CELL_WIDTH + CELL_WIDTH * 0.5;
          // Normalize x in range [-1, 1]
          const nx = (c / cols) * 2 - 1;

          // ── Multi-Harmonic 3D Wave Topography (Zeabur Contour Flow) ──
          // Wave 1: Diagonal smooth swell
          const w1 = Math.sin(nx * 3.2 - ny * 2.1 + t * 0.75);
          // Wave 2: Counter harmonic ribbon
          const w2 = Math.cos(nx * 2.0 + ny * 3.5 - t * 0.55);
          // Wave 3: Radial ripple originating from upper-right quadrant
          const rx = nx - 0.45;
          const ry = ny + 0.35;
          const distOrigin = Math.sqrt(rx * rx + ry * ry);
          const w3 = Math.sin(distOrigin * 6.5 - t * 1.1);

          // Combined elevation in range approx [-1, 1]
          let elevation = w1 * 0.45 + w2 * 0.35 + w3 * 0.20;

          // Mouse deflection lens
          const dx = px - mouse.x;
          const dy = py - mouse.y;
          const dsq = dx * dx + dy * dy;
          let hoverFactor = 0;

          if (dsq < hoverRadiusSq) {
            hoverFactor = 1 - Math.sqrt(dsq) / hoverRadius;
            elevation += hoverFactor * 0.75;
          }

          // Topographic contour bands: sharp peaks and subtle slopes
          // Elevation mapped to normalized 0..1
          const normElev = Math.max(0, Math.min(1, (elevation + 0.85) / 1.7));

          // Calculate ridge intensity using power curve for high contrast
          const ridge = Math.pow(normElev, 2.2);

          // ── Dynamic 0 / 1 Mutation & Continuous Flow ──
          const cell = grid[r][c];

          // Cells on active crests or under mouse continuously mutate digits
          const flipProbability = 0.003 + ridge * 0.06 + hoverFactor * 0.25;

          if (Math.random() < flipProbability && now - cell.lastFlip > 180) {
            // Synchronize high-intensity crests into coherent binary runs
            if (ridge > 0.65 && Math.random() < 0.4) {
              const coherentVal = Math.sin(c * 0.4 + t * 2.5) > 0 ? "1" : "0";
              cell.val = coherentVal;
            } else {
              cell.val = cell.val === "1" ? "0" : "1";
            }
            cell.lastFlip = now;
          }

          // ── Color Grading (Zeabur Palette) ──
          let fillStyle: string;

          if (hoverFactor > 0.05) {
            // Interactive mouse highlight: glowing lavender-white
            const a = Math.min(1, 0.25 + hoverFactor * 0.75);
            fillStyle = `rgba(243, 232, 255, ${a.toFixed(2)})`;
          } else if (ridge > 0.72) {
            // Crest peaks: brilliant lavender-white with high opacity
            const a = Math.min(0.96, 0.6 + (ridge - 0.72) * 1.4);
            fillStyle = `rgba(240, 230, 255, ${a.toFixed(2)})`;
          } else if (ridge > 0.45) {
            // Mid-elevation slopes: Zeabur signature purple
            const a = 0.22 + (ridge - 0.45) * 1.2;
            fillStyle = `rgba(168, 85, 247, ${a.toFixed(2)})`;
          } else if (ridge > 0.22) {
            // Low contour transition: soft muted indigo/slate
            const a = 0.08 + (ridge - 0.22) * 0.6;
            fillStyle = `rgba(129, 140, 248, ${a.toFixed(2)})`;
          } else {
            // Deep background valleys: subtle, dim slate
            fillStyle = "rgba(148, 163, 184, 0.065)";
          }

          ctx.fillStyle = fillStyle;
          ctx.fillText(cell.val, px, py);
        }
      }

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.targetX = e.clientX - rect.left;
      mouse.targetY = e.clientY - rect.top;
    };

    const onMouseLeave = () => {
      mouse.targetX = -9999;
      mouse.targetY = -9999;
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mouseleave", onMouseLeave, { passive: true });
    window.addEventListener("resize", handleResize, { passive: true });

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 1,
      }}
    />
  );
}
