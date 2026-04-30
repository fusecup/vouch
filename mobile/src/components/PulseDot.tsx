import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { colors } from '@/tokens/colors';
import { motion } from '@/tokens/motion';

interface PulseDotProps {
  size?: number;
  color?: string;
  steady?: boolean;
}

export function PulseDot({ size = 8, color = colors.pulseRed, steady = false }: PulseDotProps) {
  const progress = useSharedValue(0);

  useEffect(() => {
    if (steady) {
      progress.value = 1;
      return;
    }
    progress.value = withRepeat(
      withTiming(1, {
        duration: motion.pulse.durationMs,
        easing: Easing.inOut(Easing.ease),
      }),
      -1,
      true,
    );
  }, [progress, steady]);

  const dotStyle = useAnimatedStyle(() => {
    if (steady) return { opacity: 1, transform: [{ scale: 1 }] };
    const opacity =
      motion.pulse.minOpacity + (motion.pulse.maxOpacity - motion.pulse.minOpacity) * progress.value;
    const scale =
      motion.pulse.minScale + (motion.pulse.maxScale - motion.pulse.minScale) * progress.value;
    return { opacity, transform: [{ scale }] };
  });

  const haloStyle = useAnimatedStyle(() => {
    if (steady) return { opacity: 0 };
    return { opacity: 0.35 * (1 - progress.value), transform: [{ scale: 1 + progress.value * 1.4 }] };
  });

  return (
    <Animated.View
      style={[
        styles.wrapper,
        { width: size * 2.4, height: size * 2.4 },
      ]}
    >
      <Animated.View
        style={[
          styles.halo,
          { width: size * 2.4, height: size * 2.4, borderRadius: size * 1.2, backgroundColor: color },
          haloStyle,
        ]}
      />
      <Animated.View
        style={[
          styles.dot,
          { width: size, height: size, borderRadius: size / 2, backgroundColor: color },
          dotStyle,
        ]}
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  halo: {
    position: 'absolute',
  },
  dot: {
    shadowColor: colors.pulseRed,
    shadowOpacity: 0.9,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
});
