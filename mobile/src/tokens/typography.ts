import { Platform } from 'react-native';

const serif = Platform.select({
  ios: 'Georgia',
  android: 'serif',
  default: 'Georgia',
});

const mono = Platform.select({
  ios: 'Menlo',
  android: 'monospace',
  default: 'Menlo',
});

export const type = {
  amountHero: {
    fontFamily: serif,
    fontSize: 64,
    fontWeight: '400' as const,
    letterSpacing: -1,
  },
  amountList: {
    fontFamily: serif,
    fontSize: 36,
    fontWeight: '400' as const,
    letterSpacing: -0.5,
  },
  body: {
    fontFamily: mono,
    fontSize: 13,
    letterSpacing: 0.2,
  },
  caption: {
    fontFamily: mono,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
  },
  explainer: {
    fontFamily: serif,
    fontStyle: 'italic' as const,
    fontSize: 14,
    lineHeight: 20,
  },
  challengePhrase: {
    fontFamily: serif,
    fontSize: 28,
    lineHeight: 36,
  },
  islandTitle: {
    fontFamily: mono,
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
    fontWeight: '600' as const,
  },
} as const;
