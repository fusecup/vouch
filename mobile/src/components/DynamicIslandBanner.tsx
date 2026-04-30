import { useEffect } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { PulseDot } from '@/components/PulseDot';
import { colors } from '@/tokens/colors';
import { motion } from '@/tokens/motion';
import { type } from '@/tokens/typography';

export type IslandState =
  | { kind: 'compact'; amount: string; tier: 1 | 2 | 3 }
  | { kind: 'expanded'; amount: string; counterparty: string; specterGrade: string; approverIndex: number; approverTotal: number; onFaceId: () => void }
  | { kind: 'recording'; elapsedMs: number; totalMs: number; phrase: string }
  | { kind: 'vouched'; emotion: string; cadence: string }
  | { kind: 'coerced'; reason: string };

interface DynamicIslandBannerProps {
  state: IslandState;
  onPress?: () => void;
}

const ISLAND_COMPACT_HEIGHT = 38;
const ISLAND_EXPANDED_PAD = 18;

export function DynamicIslandBanner({ state, onPress }: DynamicIslandBannerProps) {
  const insets = useSafeAreaInsets();
  const expansion = useSharedValue(state.kind === 'compact' ? 0 : 1);

  useEffect(() => {
    expansion.value = withSpring(state.kind === 'compact' ? 0 : 1, motion.islandSpring);
  }, [state.kind, expansion]);

  const containerStyle = useAnimatedStyle(() => ({
    paddingHorizontal: 14 + expansion.value * 8,
    paddingVertical: 8 + expansion.value * 12,
  }));

  return (
    <View style={[styles.outer, { top: insets.top + 6 }]} pointerEvents="box-none">
      <Pressable onPress={onPress} disabled={!onPress}>
        <Animated.View style={[styles.island, containerStyle]}>
          {state.kind === 'compact' && <Compact state={state} />}
          {state.kind === 'expanded' && <Expanded state={state} />}
          {state.kind === 'recording' && <Recording state={state} />}
          {state.kind === 'vouched' && <Vouched state={state} />}
          {state.kind === 'coerced' && <Coerced state={state} />}
        </Animated.View>
      </Pressable>
    </View>
  );
}

function Compact({ state }: { state: Extract<IslandState, { kind: 'compact' }> }) {
  return (
    <View style={styles.compactRow}>
      <PulseDot size={7} />
      <Text style={[styles.compactAmount, { marginLeft: 10 }]}>{state.amount}</Text>
      <Text style={[styles.compactTier, { marginLeft: 10 }]}>T{state.tier}</Text>
    </View>
  );
}

function Expanded({ state }: { state: Extract<IslandState, { kind: 'expanded' }> }) {
  return (
    <View style={styles.expandedBlock}>
      <View style={styles.expandedHeaderRow}>
        <PulseDot size={7} />
        <Text style={[styles.islandTitle, { marginLeft: 10 }]}>VOUCH REQUIRED</Text>
      </View>
      <Text style={styles.expandedAmount}>
        {state.amount} → {state.counterparty}
      </Text>
      <Text style={styles.expandedMeta}>
        Specter {state.specterGrade} · approver {state.approverIndex} of {state.approverTotal}
      </Text>
      <Pressable style={styles.faceIdButton} onPress={state.onFaceId}>
        <Text style={styles.faceIdText}>Face ID →</Text>
      </Pressable>
    </View>
  );
}

function Recording({ state }: { state: Extract<IslandState, { kind: 'recording' }> }) {
  const progress = Math.min(1, state.elapsedMs / state.totalMs);
  const seconds = (state.elapsedMs / 1000).toFixed(1);
  const total = (state.totalMs / 1000).toFixed(0);
  return (
    <View style={styles.expandedBlock}>
      <View style={styles.expandedHeaderRow}>
        <PulseDot size={7} />
        <Text style={[styles.islandTitle, { marginLeft: 10 }]}>REC {seconds}s / {total}s</Text>
      </View>
      <Waveform />
      <Text style={styles.phraseTeleprompter}>&ldquo;{state.phrase}&rdquo;</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
      </View>
    </View>
  );
}

function Vouched({ state }: { state: Extract<IslandState, { kind: 'vouched' }> }) {
  return (
    <View style={styles.expandedBlock}>
      <View style={styles.expandedHeaderRow}>
        <Text style={[styles.checkGlyph]}>✓</Text>
        <Text style={[styles.islandTitle, { marginLeft: 10, color: '#3FE07D' }]}>VOUCHED</Text>
      </View>
      <Text style={styles.vouchedMeta}>
        {state.emotion} · cadence {state.cadence}
      </Text>
    </View>
  );
}

function Coerced({ state }: { state: Extract<IslandState, { kind: 'coerced' }> }) {
  return (
    <View style={[styles.expandedBlock, { backgroundColor: '#1A0000', borderColor: colors.pulseRed }]}>
      <View style={styles.expandedHeaderRow}>
        <PulseDot size={7} steady />
        <Text style={[styles.islandTitle, { marginLeft: 10, color: colors.pulseRed }]}>
          COERCED · BLOCKED
        </Text>
      </View>
      <Text style={[styles.vouchedMeta, { color: colors.pulseRed }]}>{state.reason} ▲</Text>
    </View>
  );
}

function Waveform() {
  const bars = 32;
  return (
    <View style={styles.waveform}>
      {Array.from({ length: bars }).map((_, i) => (
        <WaveformBar key={i} index={i} />
      ))}
    </View>
  );
}

function WaveformBar({ index }: { index: number }) {
  const h = useSharedValue(8);
  useEffect(() => {
    const seed = (index * 37) % 100;
    h.value = withRepeat(
      withTiming(6 + ((seed % 18) + 6), {
        duration: 280 + (seed % 220),
        easing: Easing.inOut(Easing.quad),
      }),
      -1,
      true,
    );
  }, [h, index]);
  const style = useAnimatedStyle(() => ({ height: h.value }));
  return <Animated.View style={[styles.waveBar, style]} />;
}

const styles = StyleSheet.create({
  outer: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 100,
  },
  island: {
    minHeight: ISLAND_COMPACT_HEIGHT,
    minWidth: 130,
    maxWidth: 360,
    borderRadius: 24,
    backgroundColor: '#000',
    borderWidth: 1,
    borderColor: '#1F1208',
    paddingHorizontal: 14,
    paddingVertical: 8,
    shadowColor: '#000',
    shadowOpacity: 0.85,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
  },
  compactRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  compactAmount: {
    ...type.body,
    color: colors.inkPrimary,
    fontWeight: '600',
  },
  compactTier: {
    ...type.caption,
    color: colors.accentAmber,
  },
  expandedBlock: {
    minWidth: 280,
    paddingHorizontal: ISLAND_EXPANDED_PAD,
    paddingVertical: 8,
  },
  expandedHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  islandTitle: {
    ...type.islandTitle,
    color: colors.inkPrimary,
  },
  expandedAmount: {
    ...type.body,
    fontSize: 15,
    color: colors.inkPrimary,
    marginTop: 2,
  },
  expandedMeta: {
    ...type.body,
    fontSize: 12,
    color: colors.inkMono,
    marginTop: 4,
    marginBottom: 12,
  },
  faceIdButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.accentAmber,
  },
  faceIdText: {
    ...type.caption,
    color: colors.accentAmber,
    fontSize: 12,
  },
  waveform: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 24,
    marginVertical: 8,
  },
  waveBar: {
    width: 3,
    borderRadius: 1.5,
    backgroundColor: colors.accentAmber,
  },
  phraseTeleprompter: {
    ...type.body,
    color: colors.inkPrimary,
    fontSize: 13,
    marginVertical: 6,
    fontStyle: 'italic',
  },
  progressTrack: {
    height: 3,
    backgroundColor: '#2A1A0A',
    borderRadius: 2,
    overflow: 'hidden',
    marginTop: 8,
  },
  progressFill: {
    height: 3,
    backgroundColor: colors.accentAmber,
  },
  vouchedMeta: {
    ...type.body,
    fontSize: 12,
    color: colors.inkMono,
  },
  checkGlyph: {
    color: '#3FE07D',
    fontSize: 14,
    fontWeight: '700',
  },
});
