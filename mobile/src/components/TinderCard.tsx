import { Dimensions, StyleSheet, Text, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  interpolate,
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';

import { LogoAvatar } from '@/components/LogoAvatar';
import { colors } from '@/tokens/colors';
import { motion } from '@/tokens/motion';
import { type } from '@/tokens/typography';
import { Transaction } from '@/types/transaction';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SWIPE_THRESHOLD = SCREEN_WIDTH * motion.swipeThresholdRatio;
const CARD_WIDTH = Math.min(360, SCREEN_WIDTH * 0.86);
const SCALLOP_COUNT = 14;
const SCALLOP_DIAMETER = CARD_WIDTH / SCALLOP_COUNT;

interface TinderCardProps {
  txn: Transaction;
  onApprove: (txn: Transaction) => void;
  onReject: (txn: Transaction) => void;
  onEscalate: (txn: Transaction) => void;
}

const formatAmount = (amount: number) =>
  `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

const formatTime = (iso: string) => {
  const d = new Date(iso);
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
};

function deriveBars(seed: string, count: number) {
  const bars: number[] = [];
  for (let i = 0; i < count; i += 1) {
    const c = seed.charCodeAt(i % seed.length);
    bars.push(((c + i) % 4) + 1);
  }
  return bars;
}

function deriveDigits(txn: Transaction) {
  const raw = `${txn.id}${txn.amount}${(txn.dateLabel ?? '').replace(/\D/g, '')}`.replace(/\D/g, '');
  return raw.padEnd(12, '0').slice(0, 12).split('').join(' ');
}

export function TinderCard({ txn, onApprove, onReject, onEscalate }: TinderCardProps) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const fly = (dir: 'left' | 'right' | 'up', cb: () => void) => {
    'worklet';
    const target =
      dir === 'left'
        ? { x: -SCREEN_WIDTH * 1.4, y: 0 }
        : dir === 'right'
          ? { x: SCREEN_WIDTH * 1.4, y: 0 }
          : { x: 0, y: -SCREEN_WIDTH * 1.4 };
    translateX.value = withTiming(target.x, { duration: 280 });
    translateY.value = withTiming(target.y, { duration: 280 }, (finished) => {
      if (finished) runOnJS(cb)();
    });
  };

  const pan = Gesture.Pan()
    .onChange((e) => {
      translateX.value += e.changeX;
      translateY.value += e.changeY;
    })
    .onEnd(() => {
      if (translateX.value > SWIPE_THRESHOLD) {
        fly('right', () => onApprove(txn));
      } else if (translateX.value < -SWIPE_THRESHOLD) {
        fly('left', () => onReject(txn));
      } else if (translateY.value < -SWIPE_THRESHOLD) {
        fly('up', () => onEscalate(txn));
      } else {
        translateX.value = withSpring(0, motion.cardSpring);
        translateY.value = withSpring(0, motion.cardSpring);
      }
    });

  const cardStyle = useAnimatedStyle(() => {
    const rotate = interpolate(
      translateX.value,
      [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
      [-motion.swipeRotateMaxDeg, 0, motion.swipeRotateMaxDeg],
    );
    return {
      transform: [
        { translateX: translateX.value },
        { translateY: translateY.value },
        { rotate: `${rotate}deg` },
      ],
    };
  });

  const approveOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [0, SWIPE_THRESHOLD], [0, 1], 'clamp'),
  }));
  const rejectOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [-SWIPE_THRESHOLD, 0], [1, 0], 'clamp'),
  }));
  const escalateOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateY.value, [-SWIPE_THRESHOLD, 0], [1, 0], 'clamp'),
  }));

  const bars = deriveBars(txn.id + String(txn.amount), 38);
  const digits = deriveDigits(txn);

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.cardOuter, cardStyle]}>
        <View style={styles.card}>
          {/* TOP HALF — header + amount */}
          <View style={styles.topHalf}>
            <View style={styles.headerRow}>
              <LogoAvatar
                name={txn.counterparty}
                domain={txn.domain}
                logoUrl={txn.logoUrl}
                brandColor={txn.brandColor}
                size={44}
              />
              <View style={styles.headerText}>
                <Text style={styles.counterparty}>{txn.counterparty}</Text>
                <Text style={styles.category}>{txn.category}</Text>
              </View>
            </View>

            <View style={styles.amountBlock}>
              <Text style={styles.amount}>{formatAmount(txn.amount)}</Text>
              <Text style={styles.statusLine}>VOUCH PENDING · TIER {txn.tier}</Text>
            </View>
          </View>

          {/* PERFORATION — dashed line with side punches */}
          <View style={styles.perforation}>
            <View style={[styles.perfPunch, styles.perfPunchLeft]} />
            <View style={styles.dashRow}>
              {Array.from({ length: 24 }).map((_, i) => (
                <View key={i} style={styles.dash} />
              ))}
            </View>
            <View style={[styles.perfPunch, styles.perfPunchRight]} />
          </View>

          {/* BOTTOM HALF — receipt grid + specter + barcode */}
          <View style={styles.bottomHalf}>
            <View style={styles.gridRow}>
              <ReceiptCol label="REFERENCE" value={txn.reference ?? '—'} />
              <ReceiptCol label="AMOUNT" value={formatAmount(txn.amount)} alignRight />
            </View>

            <View style={styles.gridRow}>
              <ReceiptCol
                label="DATE & TIME"
                value={`${txn.dateLabel ?? ''} · ${formatTime(txn.createdAt)}`}
              />
              <ReceiptCol
                label={txn.recurring ? 'RECURRING' : 'ONE-OFF'}
                value={txn.timeToClear ?? '—'}
                alignRight
              />
            </View>

            <View style={styles.specterInset}>
              <View style={styles.specterHeader}>
                <View style={styles.specterDots}>
                  <View style={styles.specterDot} />
                  <View style={[styles.specterDot, { marginLeft: 4 }]} />
                </View>
                <Text style={styles.specterLabel}>SPECTER</Text>
                <View style={styles.specterPill}>
                  <Text style={styles.specterPillText}>{txn.specterGrade}</Text>
                </View>
              </View>
              {txn.specterNote ? (
                <Text style={styles.specterNote}>{txn.specterNote}</Text>
              ) : (
                <Text style={styles.specterNote}>established counterparty · routine</Text>
              )}
            </View>

            {txn.explainer && (
              <Text style={styles.explainer}>&ldquo;{txn.explainer}&rdquo;</Text>
            )}

            {/* Barcode */}
            <View style={styles.barcodeBlock}>
              <View style={styles.barcodeBars}>
                {bars.map((w, i) => (
                  <View key={i} style={[styles.bar, { width: w }]} />
                ))}
              </View>
              <Text style={styles.barcodeDigits}>{digits}</Text>
            </View>
          </View>
        </View>

        {/* Scalloped tear edge — row of white half-disks below the card */}
        <View style={styles.scallopRow}>
          {Array.from({ length: SCALLOP_COUNT }).map((_, i) => (
            <View key={i} style={styles.scallop} />
          ))}
        </View>

        {/* Swipe overlay labels */}
        <Animated.View style={[styles.overlay, styles.approveOverlay, approveOverlayStyle]}>
          <Text style={[styles.overlayText, { color: '#1F8E3D' }]}>APPROVE</Text>
        </Animated.View>
        <Animated.View style={[styles.overlay, styles.rejectOverlay, rejectOverlayStyle]}>
          <Text style={[styles.overlayText, { color: colors.pulseRed }]}>REJECT</Text>
        </Animated.View>
        <Animated.View style={[styles.overlay, styles.escalateOverlay, escalateOverlayStyle]}>
          <Text style={[styles.overlayText, { color: colors.accentAmber }]}>ESCALATE</Text>
        </Animated.View>
      </Animated.View>
    </GestureDetector>
  );
}

function ReceiptCol({
  label,
  value,
  alignRight,
}: {
  label: string;
  value: string;
  alignRight?: boolean;
}) {
  return (
    <View style={[{ flex: 1 }, alignRight && { alignItems: 'flex-end' }]}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, alignRight && { textAlign: 'right' }]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  cardOuter: {
    width: CARD_WIDTH,
    alignItems: 'stretch',
    shadowColor: '#000',
    shadowOpacity: 0.55,
    shadowRadius: 36,
    shadowOffset: { width: 0, height: 24 },
    elevation: 18,
  },
  card: {
    backgroundColor: colors.cardFill,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    borderBottomWidth: 0,
    paddingBottom: 4,
  },

  topHalf: {
    paddingTop: 22,
    paddingHorizontal: 22,
    paddingBottom: 18,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  headerText: {
    flex: 1,
    gap: 2,
  },
  counterparty: {
    fontFamily: type.body.fontFamily,
    fontSize: 16,
    fontWeight: '600',
    color: colors.cardInkPrimary,
  },
  category: {
    ...type.caption,
    color: colors.cardInkSecondary,
    fontSize: 10,
  },
  amountBlock: {
    marginTop: 18,
    alignItems: 'center',
    gap: 6,
  },
  amount: {
    fontFamily: type.amountHero.fontFamily,
    fontSize: 50,
    fontWeight: '500',
    color: colors.cardInkPrimary,
    letterSpacing: -0.5,
  },
  statusLine: {
    ...type.caption,
    color: colors.cardInkMuted,
    fontSize: 9.5,
  },

  perforation: {
    height: 18,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    position: 'relative',
  },
  perfPunch: {
    position: 'absolute',
    top: '50%',
    marginTop: -9,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.bloomEdge,
  },
  perfPunchLeft: { left: -9 },
  perfPunchRight: { right: -9 },
  dashRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  dash: {
    width: 6,
    height: 1,
    backgroundColor: colors.cardStroke,
  },

  bottomHalf: {
    paddingTop: 18,
    paddingBottom: 22,
    paddingHorizontal: 22,
    gap: 16,
  },
  gridRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 16,
  },
  label: {
    ...type.caption,
    color: colors.cardInkMuted,
    fontSize: 9.5,
    marginBottom: 4,
  },
  value: {
    fontFamily: type.body.fontFamily,
    fontSize: 13,
    fontWeight: '600',
    color: colors.cardInkPrimary,
  },

  specterInset: {
    backgroundColor: colors.cardSpecterInset,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    gap: 8,
    marginTop: 4,
  },
  specterHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  specterDots: {
    flexDirection: 'row',
    marginRight: 8,
  },
  specterDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accentAmber,
  },
  specterLabel: {
    ...type.caption,
    color: colors.inkPrimary,
    fontSize: 10,
    flex: 1,
    letterSpacing: 1.4,
  },
  specterPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
    backgroundColor: 'rgba(255,138,46,0.15)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.accentAmber,
  },
  specterPillText: {
    ...type.caption,
    color: colors.accentAmber,
    fontWeight: '700',
    fontSize: 10,
  },
  specterNote: {
    fontFamily: type.body.fontFamily,
    color: colors.inkMono,
    fontSize: 12,
    lineHeight: 16,
  },

  explainer: {
    ...type.explainer,
    color: colors.accentAmber,
    fontSize: 14,
    textAlign: 'center',
  },

  barcodeBlock: {
    alignItems: 'center',
    marginTop: 6,
    gap: 6,
  },
  barcodeBars: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 38,
  },
  bar: {
    height: '100%',
    backgroundColor: colors.cardInkPrimary,
    marginRight: 1,
  },
  barcodeDigits: {
    fontFamily: type.body.fontFamily,
    fontSize: 10,
    letterSpacing: 1.6,
    color: colors.cardInkPrimary,
  },

  scallopRow: {
    flexDirection: 'row',
    width: CARD_WIDTH,
    height: SCALLOP_DIAMETER / 2,
    overflow: 'hidden',
    backgroundColor: 'transparent',
  },
  scallop: {
    width: SCALLOP_DIAMETER,
    height: SCALLOP_DIAMETER,
    borderRadius: SCALLOP_DIAMETER / 2,
    backgroundColor: colors.cardFill,
    marginTop: -SCALLOP_DIAMETER / 2,
  },

  overlay: {
    position: 'absolute',
    top: 22,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 2,
    backgroundColor: 'rgba(255,253,248,0.92)',
    zIndex: 10,
  },
  approveOverlay: {
    right: 22,
    borderColor: '#1F8E3D',
  },
  rejectOverlay: {
    left: 22,
    borderColor: colors.pulseRed,
  },
  escalateOverlay: {
    left: '50%',
    transform: [{ translateX: -50 }],
    borderColor: colors.accentAmber,
  },
  overlayText: {
    ...type.caption,
    fontSize: 14,
    fontWeight: '700',
  },
});
