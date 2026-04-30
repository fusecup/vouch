import { forwardRef, useImperativeHandle } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';

export interface MediaCaptureHandle {
  start: () => Promise<void>;
  stop: () => Promise<{ audioBlob: Blob; mimeType: string }>;
  cancel: () => void;
}

interface MediaCaptureProps {
  onError?: (msg: string) => void;
}

/**
 * Native placeholder — to be replaced by an expo-camera + expo-av implementation
 * once `expo prebuild` runs. Holds the same interface so callers don't branch.
 */
export const MediaCapture = forwardRef<MediaCaptureHandle, MediaCaptureProps>((_props, ref) => {
  useImperativeHandle(ref, () => ({
    async start() {
      /* native capture wired post-prebuild */
    },
    async stop() {
      return { audioBlob: new Blob(), mimeType: 'audio/m4a' };
    },
    cancel() {
      /* no-op */
    },
  }));

  return (
    <View style={styles.frame}>
      <Text style={styles.label}>[ camera feed — native build ]</Text>
    </View>
  );
});

MediaCapture.displayName = 'MediaCapture';

const styles = StyleSheet.create({
  frame: {
    width: '78%',
    aspectRatio: 0.72,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    backgroundColor: '#0A0604',
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    ...type.caption,
    color: colors.inkMuted,
  },
});
