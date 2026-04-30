import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BloomGradient } from '@/components/BloomGradient';
import { DynamicIslandBanner, IslandState } from '@/components/DynamicIslandBanner';
import { MediaCapture, MediaCaptureHandle } from '@/components/MediaCapture';
import { pendingTransactions } from '@/data/mockTransactions';
import { promptBiometric } from '@/services/biometric';
import {
  classifyAudio,
  EmotionResult,
  isClassifierReady,
  preloadEmotionClassifier,
} from '@/services/emotion';
import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';

const RECORDING_TOTAL_MS = 8000;

type Stage = 'compact' | 'expanded' | 'faceid' | 'recording' | 'classifying' | 'result';

export default function VouchScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ id?: string; mode?: string }>();

  const txn = useMemo(
    () => pendingTransactions.find((t) => t.id === params.id) ?? pendingTransactions.find((t) => t.tier === 3)!,
    [params.id],
  );

  const [stage, setStage] = useState<Stage>('expanded');
  const [recordingMs, setRecordingMs] = useState(0);
  const [duress, setDuress] = useState(false);
  const [approverIndex, setApproverIndex] = useState(1);
  const [biometricError, setBiometricError] = useState<string | null>(null);
  const [biometricMethod, setBiometricMethod] = useState<string | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const formatAmount = (amount: number) =>
    `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

  const challengePhrase = `authorize ${amountWords(txn.amount)} to ${txn.counterparty}`;

  const startRecording = () => {
    setStage('recording');
    setRecordingMs(0);
    tickRef.current = setInterval(() => {
      setRecordingMs((ms) => {
        const next = ms + 100;
        if (next >= RECORDING_TOTAL_MS) {
          if (tickRef.current) clearInterval(tickRef.current);
          setStage('result');
          return RECORDING_TOTAL_MS;
        }
        return next;
      });
    }, 100);
  };

  const beginFaceId = async () => {
    setStage('faceid');
    setBiometricError(null);
    const result = await promptBiometric();
    if (result.ok) {
      setBiometricMethod(result.method);
      startRecording();
    } else {
      const labels: Record<string, string> = {
        cancelled: 'cancelled by user',
        unavailable: 'biometric unavailable on this device',
        no_hardware: 'no biometric hardware',
        failed: 'authentication failed',
      };
      setBiometricError(labels[result.reason] ?? result.reason);
      setStage('expanded');
    }
  };

  useEffect(() => {
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, []);

  const reset = () => {
    setStage('expanded');
    setRecordingMs(0);
  };

  const islandState: IslandState =
    stage === 'expanded' || stage === 'faceid'
      ? {
          kind: 'expanded',
          amount: formatAmount(txn.amount),
          counterparty: txn.counterparty,
          specterGrade: txn.specterGrade,
          approverIndex,
          approverTotal: txn.approversRequired ?? 3,
          onFaceId: beginFaceId,
        }
      : stage === 'recording'
        ? {
            kind: 'recording',
            elapsedMs: recordingMs,
            totalMs: RECORDING_TOTAL_MS,
            phrase: challengePhrase,
          }
        : duress
          ? { kind: 'coerced', reason: 'rushed cadence' }
          : { kind: 'vouched', emotion: 'neutral', cadence: 'ok' };

  return (
    <BloomGradient>
      <DynamicIslandBanner state={islandState} />

      <View style={[styles.header, { paddingTop: insets.top + 64 }]}>
        <View style={styles.headerLeftBlock}>
          <Text style={styles.tier2Label}>TIER 2 · BIOMETRIC VOUCH</Text>
          <Text style={styles.subhead}>{txn.counterparty}</Text>
        </View>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.back}>✕</Text>
        </Pressable>
      </View>

      <View style={styles.body}>
        {stage === 'expanded' && <ExpandedHint error={biometricError} />}
        {stage === 'faceid' && <FaceIdGate />}
        {stage === 'recording' && <RecordingFrame phrase={challengePhrase} />}
        {stage === 'result' && (
          <ResultFrame
            duress={duress}
            biometricMethod={biometricMethod}
            approverIndex={approverIndex}
            approverTotal={txn.approversRequired ?? 3}
            onAdvanceApprover={() => {
              if (approverIndex < (txn.approversRequired ?? 3)) {
                setApproverIndex((i) => i + 1);
                reset();
              } else {
                router.replace('/');
              }
            }}
          />
        )}
      </View>

      <View style={[styles.devRow, { paddingBottom: insets.bottom + 12 }]}>
        <Text style={styles.devLabel}>DEMO</Text>
        <Pressable
          onPress={() => setDuress((d) => !d)}
          style={[styles.toggle, duress && styles.toggleOn]}
        >
          <Text style={[styles.toggleText, duress && styles.toggleTextOn]}>
            duress: {duress ? 'on' : 'off'}
          </Text>
        </Pressable>
        <Pressable onPress={reset} style={styles.toggle}>
          <Text style={styles.toggleText}>reset</Text>
        </Pressable>
      </View>
    </BloomGradient>
  );
}

function ExpandedHint({ error }: { error: string | null }) {
  return (
    <View style={styles.hintBlock}>
      <Text style={styles.hintTitle}>VOUCH FROM THE ISLAND</Text>
      <Text style={styles.hintBody}>
        Tap <Text style={styles.hintEmph}>Face ID</Text> in the Dynamic Island above to begin the
        challenge-phrase capture.
      </Text>
      {error && <Text style={styles.errorLine}>{error}</Text>}
    </View>
  );
}

function FaceIdGate() {
  return (
    <View style={styles.faceIdFrame}>
      <View style={styles.faceIdRing}>
        <Text style={styles.faceIdGlyph}>◉</Text>
      </View>
      <Text style={styles.faceIdLabel}>WAITING FOR BIOMETRIC</Text>
      <Text style={styles.faceIdHint}>complete the prompt on your device</Text>
    </View>
  );
}

function RecordingFrame({ phrase }: { phrase: string }) {
  return (
    <View style={styles.recordingFrame}>
      <View style={styles.cameraStub}>
        <Text style={styles.cameraStubLabel}>[ camera feed ]</Text>
      </View>
      <Text style={styles.teleprompter}>&ldquo;{phrase}&rdquo;</Text>
    </View>
  );
}

function ResultFrame({
  duress,
  biometricMethod,
  approverIndex,
  approverTotal,
  onAdvanceApprover,
}: {
  duress: boolean;
  biometricMethod: string | null;
  approverIndex: number;
  approverTotal: number;
  onAdvanceApprover: () => void;
}) {
  const methodLabel =
    biometricMethod === 'face'
      ? 'Face ID'
      : biometricMethod === 'fingerprint'
        ? 'Touch ID'
        : biometricMethod === 'webauthn'
          ? 'Platform authenticator'
          : 'biometric';
  if (duress) {
    return (
      <View style={[styles.resultFrame, { borderColor: colors.pulseRed, backgroundColor: '#1A0000' }]}>
        <Text style={[styles.resultGlyph, { color: colors.pulseRed }]}>●</Text>
        <Text style={[styles.resultTitle, { color: colors.pulseRed }]}>COERCED · BLOCKED</Text>
        <Text style={styles.resultBody}>
          rushed cadence detected · facial mismatch ▲{'\n'}
          this attestation cannot be overridden
        </Text>
      </View>
    );
  }
  const last = approverIndex >= approverTotal;
  return (
    <View style={styles.resultFrame}>
      <Text style={[styles.resultGlyph, { color: '#3FE07D' }]}>✓</Text>
      <Text style={styles.resultTitle}>VOUCHED</Text>
      <Text style={styles.resultBody}>
        {methodLabel} verified · neutral · cadence ok{'\n'}
        approver {approverIndex} of {approverTotal} complete
      </Text>
      <Pressable style={styles.advanceButton} onPress={onAdvanceApprover}>
        <Text style={styles.advanceText}>{last ? 'EXECUTE PAYMENT' : 'NEXT APPROVER →'}</Text>
      </Pressable>
    </View>
  );
}

function amountWords(amount: number): string {
  if (amount === 62000) return 'sixty-two thousand';
  if (amount >= 1000) return `${(amount / 1000).toFixed(0)} thousand`;
  return `${amount}`;
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerLeftBlock: {
    gap: 6,
  },
  tier2Label: {
    ...type.caption,
    color: colors.pulseRed,
  },
  subhead: {
    ...type.body,
    color: colors.inkMono,
  },
  back: {
    color: colors.inkMono,
    fontSize: 18,
  },
  body: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hintBlock: {
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 20,
  },
  hintTitle: {
    ...type.caption,
    color: colors.inkMono,
  },
  hintBody: {
    ...type.body,
    color: colors.inkMono,
    textAlign: 'center',
    fontSize: 14,
  },
  hintEmph: {
    color: colors.accentAmber,
  },
  errorLine: {
    ...type.caption,
    color: colors.pulseRed,
    marginTop: 8,
  },
  faceIdFrame: {
    alignItems: 'center',
    gap: 14,
  },
  faceIdRing: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 1.5,
    borderColor: colors.accentAmber,
    alignItems: 'center',
    justifyContent: 'center',
  },
  faceIdGlyph: {
    fontSize: 60,
    color: colors.accentAmber,
  },
  faceIdLabel: {
    ...type.caption,
    color: colors.inkPrimary,
    fontSize: 14,
  },
  faceIdHint: {
    ...type.caption,
    color: colors.inkMono,
  },
  recordingFrame: {
    alignItems: 'center',
    gap: 22,
    width: '100%',
  },
  cameraStub: {
    width: '78%',
    aspectRatio: 0.72,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    backgroundColor: '#0A0604',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cameraStubLabel: {
    ...type.caption,
    color: colors.inkMuted,
  },
  teleprompter: {
    ...type.challengePhrase,
    color: colors.inkPrimary,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  resultFrame: {
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 24,
    paddingVertical: 28,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    backgroundColor: colors.cardFill,
  },
  resultGlyph: {
    fontSize: 28,
  },
  resultTitle: {
    ...type.caption,
    color: '#3FE07D',
    fontSize: 14,
  },
  resultBody: {
    ...type.body,
    color: colors.inkMono,
    textAlign: 'center',
    lineHeight: 19,
  },
  advanceButton: {
    marginTop: 16,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.accentAmber,
  },
  advanceText: {
    ...type.caption,
    color: colors.accentAmber,
  },
  devRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  devLabel: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 9,
    marginRight: 8,
  },
  toggle: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.inkMuted,
  },
  toggleOn: {
    borderColor: colors.pulseRed,
    backgroundColor: 'rgba(255,59,48,0.12)',
  },
  toggleText: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 10,
  },
  toggleTextOn: {
    color: colors.pulseRed,
  },
});
