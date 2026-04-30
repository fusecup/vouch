import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';

export interface ApproverRecording {
  approverIndex: number;
  videoUrl: string;
  vouched: boolean;
  emotionLabel: string;
  emotionScore: number;
  capturedAt: Date;
  durationSec: number;
  reason?: string;
}

interface ApproverPlaybackProps {
  recording: ApproverRecording;
}

export function ApproverPlayback({ recording }: ApproverPlaybackProps) {
  const accent = recording.vouched ? '#3FE07D' : colors.pulseRed;
  const status = recording.vouched ? 'VOUCHED' : 'COERCED · BLOCKED';
  return (
    <View style={[styles.card, !recording.vouched && { borderColor: colors.pulseRed }]}>
      <View style={styles.headerRow}>
        <Text style={[styles.label, { color: accent }]}>
          APPROVER {recording.approverIndex} · {status}
        </Text>
        <Text style={styles.timestamp}>
          {recording.capturedAt.toLocaleTimeString()}
        </Text>
      </View>
      <View style={styles.videoStub}>
        <Text style={styles.stubLabel}>[ playback — native build ]</Text>
      </View>
      <Text style={styles.meta}>
        {recording.emotionLabel} · {(recording.emotionScore * 100).toFixed(0)}% · {recording.durationSec.toFixed(1)}s
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardFill,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    padding: 14,
    gap: 12,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    ...type.caption,
    fontSize: 11,
    fontWeight: '700',
  },
  timestamp: {
    ...type.caption,
    color: colors.cardInkMuted,
    fontSize: 9,
  },
  videoStub: {
    aspectRatio: 0.78,
    borderRadius: 12,
    backgroundColor: '#0A0604',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stubLabel: {
    ...type.caption,
    color: colors.inkMuted,
  },
  meta: {
    ...type.body,
    color: colors.cardInkSecondary,
    fontSize: 11,
  },
});
