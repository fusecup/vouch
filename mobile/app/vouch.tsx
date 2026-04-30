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
  const [emotionResult, setEmotionResult] = useState<EmotionResult | null>(null);
  const [classifierLoading, setClassifierLoading] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const captureRef = useRef<MediaCaptureHandle>(null);

  const formatAmount = (amount: number) =>
    `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

  const challengePhrase = `authorize ${amountWords(txn.amount)} to ${txn.counterparty}`;

  // Kick off the in-browser model load as soon as the screen mounts so the
  // user has it warmed by the time they finish the 8s capture.
  useEffect(() => {
    setClassifierLoading(!isClassifierReady());
    preloadEmotionClassifier()
      .catch(() => {/* falls back to heuristic */})
      .finally(() => setClassifierLoading(false));
  }, []);

  const finishRecording = async () => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    setStage('classifying');
    let audioBlob: Blob = new Blob();
    try {
      const stopped = await captureRef.current?.stop();
      if (stopped) audioBlob = stopped.audioBlob;
    } catch {
      /* ignore — fall through to classification */
    }
    try {
      if (audioBlob.size > 0) {
        const result = await classifyAudio(audioBlob);
        setEmotionResult(result);
      } else {
        setEmotionResult({ label: 'no audio', score: 0, family: 'unknown' });
      }
    } catch (e) {
      setEmotionResult({
        label: 'classifier error',
        score: 0,
        family: 'unknown',
      });
    }
    setStage('result');
  };

  const startRecording = async () => {
    setStage('recording');
    setRecordingMs(0);
    setEmotionResult(null);

    try {
      await captureRef.current?.start();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'capture failed';
      setBiometricError(`capture: ${msg}`);
      setStage('expanded');
      return;
    }

    tickRef.current = setInterval(() => {
      setRecordingMs((ms) => {
        const next = ms + 100;
        if (next >= RECORDING_TOTAL_MS) {
          if (tickRef.current) clearInterval(tickRef.current);
          tickRef.current = null;
          // queue the async finishRecording outside the setter
          setTimeout(() => {
            finishRecording();
          }, 0);
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
      await startRecording();
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
      captureRef.current?.cancel();
    };
  }, []);

  const reset = () => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    captureRef.current?.cancel();
    setStage('expanded');
    setRecordingMs(0);
    setEmotionResult(null);
  };

  const isCoerced =
    duress || (emotionResult?.family === 'coerced');

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
        : stage === 'classifying'
          ? {
              kind: 'recording',
              elapsedMs: RECORDING_TOTAL_MS,
              totalMs: RECORDING_TOTAL_MS,
              phrase: 'analysing emotion…',
            }
          : isCoerced
            ? {
                kind: 'coerced',
                reason: duress ? 'rushed cadence' : (emotionResult?.label ?? 'coerced'),
              }
            : {
                kind: 'vouched',
                emotion: emotionResult?.label ?? 'neutral',
                cadence: 'ok',
              };

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
        {stage === 'expanded' && (
          <ExpandedHint error={biometricError} classifierLoading={classifierLoading} />
        )}
        {stage === 'faceid' && <FaceIdGate />}
        {(stage === 'recording' || stage === 'classifying') && (
          <RecordingFrame
            phrase={challengePhrase}
            captureRef={captureRef}
            classifying={stage === 'classifying'}
          />
        )}
        {stage === 'result' && (
          <ResultFrame
            duress={duress}
            biometricMethod={biometricMethod}
            emotionResult={emotionResult}
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

function ExpandedHint({
  error,
  classifierLoading,
}: {
  error: string | null;
  classifierLoading: boolean;
}) {
  return (
    <View style={styles.hintBlock}>
      <Text style={styles.hintTitle}>VOUCH FROM THE ISLAND</Text>
      <Text style={styles.hintBody}>
        Tap <Text style={styles.hintEmph}>Face ID</Text> in the Dynamic Island above to begin the
        challenge-phrase capture.
      </Text>
      {classifierLoading && (
        <Text style={styles.classifierLine}>warming voice classifier…</Text>
      )}
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

function RecordingFrame({
  phrase,
  captureRef,
  classifying,
}: {
  phrase: string;
  captureRef: React.RefObject<MediaCaptureHandle | null>;
  classifying: boolean;
}) {
  return (
    <View style={styles.recordingFrame}>
      <View style={styles.cameraStub}>
        <MediaCapture ref={captureRef as React.Ref<MediaCaptureHandle>} />
      </View>
      <Text style={styles.teleprompter}>
        {classifying ? 'analysing voice…' : `“${phrase}”`}
      </Text>
    </View>
  );
}

function ResultFrame({
  duress,
  biometricMethod,
  emotionResult,
  approverIndex,
  approverTotal,
  onAdvanceApprover,
}: {
  duress: boolean;
  biometricMethod: string | null;
  emotionResult: EmotionResult | null;
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

  const coerced = duress || emotionResult?.family === 'coerced';
  const reason =
    duress
      ? 'rushed cadence (duress override)'
      : emotionResult
        ? `${emotionResult.label} · score ${(emotionResult.score * 100).toFixed(0)}%`
        : 'unknown';
  const features = emotionResult?.features;

  if (coerced) {
    return (
      <View style={[styles.resultFrame, { borderColor: colors.pulseRed, backgroundColor: '#1A0000' }]}>
        <Text style={[styles.resultGlyph, { color: colors.pulseRed }]}>●</Text>
        <Text style={[styles.resultTitle, { color: colors.pulseRed }]}>COERCED · BLOCKED</Text>
        <Text style={styles.resultBody}>
          {reason} ▲{'\n'}
          this attestation cannot be overridden
        </Text>
        {features && (
          <Text style={styles.featureLine}>
            {features.durationSec.toFixed(1)}s · rms σ²={features.rmsVariance.toFixed(4)} · syl/s={features.syllableRate.toFixed(1)}
          </Text>
        )}
      </View>
    );
  }
  const last = approverIndex >= approverTotal;
  return (
    <View style={styles.resultFrame}>
      <Text style={[styles.resultGlyph, { color: '#3FE07D' }]}>✓</Text>
      <Text style={styles.resultTitle}>VOUCHED</Text>
      <Text style={styles.resultBody}>
        {methodLabel} verified · {reason}{'\n'}
        approver {approverIndex} of {approverTotal} complete
      </Text>
      {features && (
        <Text style={styles.featureLine}>
          {features.durationSec.toFixed(1)}s · centroid {features.spectralCentroid.toFixed(0)} Hz · syl/s {features.syllableRate.toFixed(1)}
        </Text>
      )}
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
  classifierLine: {
    ...type.caption,
    color: colors.accentAmber,
    marginTop: 8,
    fontSize: 10,
  },
  featureLine: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 9,
    marginTop: 8,
    textAlign: 'center',
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
