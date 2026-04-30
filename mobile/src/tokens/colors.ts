export const colors = {
  bloomStart: '#FF6A1A',
  bloomMid: '#8A2A05',
  bloomWarmBlack: '#1A0A04',
  bloomBlack: '#050505',
  bloomEdge: '#000000',

  cardFill: '#000000',
  cardStroke: '#2A1A0A',

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
