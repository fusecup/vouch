import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';

import { colors } from '@/tokens/colors';

interface BloomGradientProps {
  children: React.ReactNode;
}

export function BloomGradient({ children }: BloomGradientProps) {
  return (
    <View style={styles.root}>
      <LinearGradient
        colors={[
          colors.bloomStart,
          colors.bloomMid,
          colors.bloomWarmBlack,
          colors.bloomBlack,
          colors.bloomEdge,
        ]}
        locations={[0, 0.18, 0.45, 0.75, 1]}
        start={{ x: 1, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.darkenOverlay} pointerEvents="none" />
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bloomEdge,
  },
  darkenOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.18)',
  },
});
