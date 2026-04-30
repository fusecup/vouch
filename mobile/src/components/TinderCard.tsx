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

import { colors } from '@/tokens/colors';
import { motion } from '@/tokens/motion';
import { type } from '@/tokens/typography';
import { Transaction } from '@/types/transaction';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SWIPE_THRESHOLD = SCREEN_WIDTH * motion.swipeThresholdRatio;

interface TinderCardProps {
  txn: Transaction;
  onApprove: (txn: Transaction) => void;
  onReject: (txn: Transaction) => void;
  onEscalate: (txn: Transaction) => void;
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

  const formatAmount = (amount: number) =>
    `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.card, cardStyle]}>
        <Text style={styles.counterparty}>{txn.counterparty.toUpperCase()}</Text>
        <View style={styles.divider} />

        <Text style={styles.amount}>{formatAmount(txn.amount)}</Text>

        <View style={styles.specterBlock}>
          <Text style={styles.specterLabel}>
            ●● Specter <Text style={styles.specterGrade}>{txn.specterGrade}</Text>
          </Text>
          {txn.specterNote && <Text style={styles.specterNote}>{txn.specterNote}</Text>}
          <Text style={styles.priorPayments}>
            {txn.priorPayments > 0
              ? `${txn.priorPayments} prior payments${txn.lastPaidAt ? ` · last ${txn.lastPaidAt}` : ''}`
              : 'first-time recipient'}
          </Text>
        </View>

        <View style={styles.divider} />

        {txn.explainer && (
          <Text style={styles.explainer}>&ldquo;{txn.explainer}&rdquo;</Text>
        )}

        <Animated.View style={[styles.overlay, styles.approveOverlay, approveOverlayStyle]}>
          <Text style={[styles.overlayText, { color: '#3FE07D' }]}>APPROVE</Text>
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

const styles = StyleSheet.create({
  card: {
    width: SCREEN_WIDTH * 0.84,
    minHeight: SCREEN_WIDTH * 1.18,
    borderRadius: 18,
    backgroundColor: colors.cardFill,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    padding: 28,
    shadowColor: '#000',
    shadowOpacity: 0.55,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 18 },
    elevation: 16,
  },
  counterparty: {
    ...type.caption,
    color: colors.inkMono,
    fontSize: 13,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.cardStroke,
    marginVertical: 22,
  },
  amount: {
    ...type.amountHero,
    color: colors.inkPrimary,
    marginBottom: 6,
  },
  specterBlock: {
    marginTop: 22,
    gap: 6,
  },
  specterLabel: {
    ...type.body,
    color: colors.inkMono,
  },
  specterGrade: {
    color: colors.accentAmber,
    fontWeight: '600',
  },
  specterNote: {
    ...type.body,
    color: colors.inkMono,
    fontSize: 12,
  },
  priorPayments: {
    ...type.body,
    color: colors.inkMuted,
    fontSize: 12,
  },
  explainer: {
    ...type.explainer,
    color: colors.accentAmber,
  },
  overlay: {
    position: 'absolute',
    top: 24,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 2,
  },
  approveOverlay: {
    right: 24,
    borderColor: '#3FE07D',
  },
  rejectOverlay: {
    left: 24,
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
