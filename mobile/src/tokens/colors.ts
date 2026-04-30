export const colors = {
  bloomStart: '#FF6A1A',
  bloomMid: '#8A2A05',
  bloomWarmBlack: '#1A0A04',
  bloomBlack: '#050505',
  bloomEdge: '#000000',

  cardFill: '#FFFDF8',
  cardStroke: '#E8E2D6',
  cardInkPrimary: '#0A0A0A',
  cardInkSecondary: '#6B5C45',
  cardInkMuted: '#9A8E78',
  cardSubFill: '#F5F1E8',
  cardSpecterInset: '#0A0A0A',

  inkPrimary: '#FFFFFF',
  inkMono: '#C9B89A',
  inkMuted: '#5A5A5A',

  accentAmber: '#FF8A2E',
  pulseRed: '#FF3B30',

  tier0: '#5A5A5A',
  tier1: '#FF8A2E',
  tier2: '#FF3B30',
} as const;

export type ColorToken = keyof typeof colors;
