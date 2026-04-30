export const motion = {
  pulse: {
    durationMs: 1400,
    minOpacity: 0.4,
    maxOpacity: 1.0,
    minScale: 0.92,
    maxScale: 1.0,
  },
  cardSpring: {
    damping: 18,
    stiffness: 200,
    mass: 0.6,
  },
  swipeRotateMaxDeg: 8,
  swipeThresholdRatio: 0.28,
  islandSpring: {
    damping: 18,
    stiffness: 200,
    mass: 0.7,
  },
} as const;
