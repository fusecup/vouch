import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApproverPlayback, ApproverRecording } from '@/components/ApproverPlayback';
import { BloomGradient } from '@/components/BloomGradient';
import { DynamicIslandBanner, IslandState } from '@/components/DynamicIslandBanner';
import { LogoAvatar } from '@/components/LogoAvatar';
import { MediaCaptureHandle } from '@/components/MediaCapture';
import { findNextPendingTier3, pendingTransactions } from '@/data/mockTransactions';
import { promptBiometric } from '@/services/biometric';
import {
  classifyAudio,
  EmotionResult,
  isClassifierReady,
  preloadEmotionClassifier,
} from '@/services/emotion';
import { classifyFaceFrame, FaceEmotionResult } from '@/services/faceEmotion';
import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';
import { Transaction } from '@/types/transaction';

const RECORDING_TOTAL_MS = 8000;
const FLASH_DURATION_MS = 1800;
const COMPLETED_DELAY_MS = 1400;

type Stage =
  | 'expanded'
  | 'faceid'
  | 'recording'
  | 'classifying'
  | 'flashing'
  | 'awaiting_remote'
  | 'completed';

const REMOTE_APPROVER = {
  name: 'Sarah Chen',
  role: 'Co-founder',
  device: 'iPhone',
};
const REMOTE_VOUCH_DELAY_MS = 3200;

export default function VouchScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ id?: string }>();

  const txn = useMemo<Transaction>(
    () =>
      pendingTransactions.find((t) => t.id === params.id) ??
      pendingTransactions.find((t) => t.tier === 3)!,
    [params.id],
  );

  const [stage, setStage] = useState<Stage>('expanded');
  const [recordingMs, setRecordingMs] = useState(0);
  const [duress, setDuress] = useState(false);
  const [approverIndex, setApproverIndex] = useState(1);
  const [biometricError, setBiometricError] = useState<string | null>(null);
  const [biometricMethod, setBiometricMethod] = useState<string | null>(null);
  const [classifierLoading, setClassifierLoading] = useState(false);
  const [recordings, setRecordings] = useState<ApproverRecording[]>([]);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [latestEmotion, setLatestEmotion] = useState<EmotionResult | null>(null);
  const [latestFace, setLatestFace] = useState<FaceEmotionResult | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const captureRef = useRef<MediaCaptureHandle>(null);

  const approversRequired = txn.approversRequired ?? 3;
  const challengePhrase = `authorize ${amountWords(txn.amount)} to ${txn.counterparty}`;

  useEffect(() => {
    setClassifierLoading(!isClassifierReady());
    preloadEmotionClassifier()
      .catch(() => {/* heuristic fallback */})
      .finally(() => setClassifierLoading(false));
  }, []);

  // Reset everything when navigating to a new txn.
  useEffect(() => {
    setStage('expanded');
    setRecordingMs(0);
    setApproverIndex(1);
    setRecordings((prev) => {
      prev.forEach((r) => URL.revokeObjectURL(r.videoUrl));
      return [];
    });
    setLatestEmotion(null);
    setLatestFace(null);
    setFlashMessage(null);
    setBiometricError(null);
    setDuress(false);
  }, [txn.id]);

  // Cleanup video object URLs on unmount.
  useEffect(() => {
    return () => {
      recordings.forEach((r) => URL.revokeObjectURL(r.videoUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const finishRecording = async () => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }

    // Snapshot the live preview before stopping the stream so Gemini has a
    // frame to score.
    const frameDataUrl = captureRef.current?.captureFrameDataUrl?.() ?? null;
    setStage('classifying');

    let audioBlob = new Blob();
    let videoBlob = new Blob();
    try {
      const stopped = await captureRef.current?.stop();
      if (stopped) {
        audioBlob = stopped.audioBlob;
        videoBlob = stopped.videoBlob;
      }
    } catch {
      /* ignore */
    }

    // Voice + face classifiers in parallel.
    const [audioRes, faceRes] = await Promise.all([
      (async (): Promise<EmotionResult> => {
        try {
          return audioBlob.size > 0
            ? await classifyAudio(audioBlob)
            : { label: 'no audio', score: 0, family: 'unknown' };
        } catch {
          return { label: 'classifier error', score: 0, family: 'unknown' };
        }
      })(),
      (async (): Promise<FaceEmotionResult | null> => {
        try {
          return frameDataUrl ? await classifyFaceFrame(frameDataUrl) : null;
        } catch {
          return null;
        }
      })(),
    ]);

    setLatestEmotion(audioRes);
    setLatestFace(faceRes);

    const voiceCoerced = audioRes.family === 'coerced';
    const faceCoerced = faceRes?.family === 'coerced';
    const coerced = duress || voiceCoerced || faceCoerced;

    const reason = duress
      ? 'rushed cadence (duress override)'
      : voiceCoerced && faceCoerced
        ? `voice ${audioRes.label} + face ${faceRes!.label}`
        : voiceCoerced
          ? `voice: ${audioRes.label} · ${(audioRes.score * 100).toFixed(0)}%`
          : faceCoerced
            ? `face: ${faceRes!.label} · ${(faceRes!.confidence * 100).toFixed(0)}%`
            : undefined;

    const combinedLabel = faceRes
      ? `voice ${audioRes.label} · face ${faceRes.label}`
      : audioRes.label;
    const combinedScore = faceRes
      ? Math.max(audioRes.score, faceRes.confidence)
      : audioRes.score;

    const videoUrl = videoBlob.size > 0 ? URL.createObjectURL(videoBlob) : '';

    const recording: ApproverRecording = {
      approverIndex,
      videoUrl,
      vouched: !coerced,
      emotionLabel: combinedLabel,
      emotionScore: combinedScore,
      capturedAt: new Date(),
      durationSec: audioRes.features?.durationSec ?? 8,
      reason,
    };
    setRecordings((prev) => [...prev, recording]);

    if (coerced) {
      setFlashMessage(`APPROVER ${approverIndex} · COERCED · BLOCKED`);
      setStage('flashing');
      setTimeout(() => {
        setStage('completed');
        setFlashMessage(null);
      }, FLASH_DURATION_MS * 2);
      return;
    }

    const isLast = approverIndex >= approversRequired;
    setFlashMessage(
      isLast
        ? `ALL ${approversRequired} VOUCHES IN — EXECUTING`
        : `APPROVER ${approverIndex} VOUCHED · NOTIFYING ${REMOTE_APPROVER.name.toUpperCase()}`,
    );
    setStage('flashing');

    setTimeout(() => {
      if (isLast) {
        setStage('completed');
        setFlashMessage(null);
        // brief breath on completed state, then move to next txn
        setTimeout(() => {
          const next = findNextPendingTier3(txn.id);
          if (next) {
            router.replace({ pathname: '/vouch', params: { id: next.id } });
          } else {
            router.replace('/');
          }
        }, COMPLETED_DELAY_MS);
      } else {
        // Subsequent approvers vouch remotely on their own device. We
        // surface that off-screen state, then synthesize a vouched
        // attestation after a short delay so the demo flows.
        setApproverIndex((i) => i + 1);
        setStage('awaiting_remote');
        setFlashMessage(null);
      }
    }, FLASH_DURATION_MS);
  };

  const startRecording = () => {
    setStage('recording');
    setRecordingMs(0);
    setBiometricError(null);
  };

  // Off-screen approver — auto-vouch after a short delay so the demo flows.
  useEffect(() => {
    if (stage !== 'awaiting_remote') return;
    let cancelled = false;
    const timer = setTimeout(() => {
      if (cancelled) return;
      const remoteRecording: ApproverRecording = {
        approverIndex,
        videoUrl: '',
        vouched: true,
        emotionLabel: 'remote vouch',
        emotionScore: 1,
        capturedAt: new Date(),
        durationSec: 0,
      };
      setRecordings((prev) => [...prev, remoteRecording]);
      setFlashMessage(`ALL ${approversRequired} VOUCHES IN — EXECUTING`);
      setStage('flashing');
      setTimeout(() => {
        setStage('completed');
        setFlashMessage(null);
        setTimeout(() => {
          const next = findNextPendingTier3(txn.id);
          if (next) {
            router.replace({ pathname: '/vouch', params: { id: next.id } });
          } else {
            router.replace('/');
          }
        }, COMPLETED_DELAY_MS);
      }, FLASH_DURATION_MS);
    }, REMOTE_VOUCH_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  // Drive capture + timer from the stage transition so the MediaCapture child
  // is guaranteed to be mounted before we call start().
  useEffect(() => {
    if (stage !== 'recording') return;

    let cancelled = false;
    let interval: ReturnType<typeof setInterval> | null = null;

    const begin = async () => {
      try {
        await captureRef.current?.start();
      } catch (e) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : 'capture failed';
        setBiometricError(msg);
        setStage('expanded');
        return;
      }
      if (cancelled) return;

      interval = setInterval(() => {
        setRecordingMs((ms) => {
          const next = ms + 100;
          if (next >= RECORDING_TOTAL_MS) {
            if (interval) clearInterval(interval);
            interval = null;
            setTimeout(() => finishRecording(), 0);
            return RECORDING_TOTAL_MS;
          }
          return next;
        });
      }, 100);
      tickRef.current = interval;
    };

    begin();

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
      tickRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

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

  const reset = () => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    captureRef.current?.cancel();
    recordings.forEach((r) => URL.revokeObjectURL(r.videoUrl));
    setStage('expanded');
    setRecordingMs(0);
    setRecordings([]);
    setApproverIndex(1);
    setLatestEmotion(null);
    setLatestFace(null);
    setFlashMessage(null);
  };

  const formatAmount = (amount: number) =>
    `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

  const islandState: IslandState =
    stage === 'expanded' || stage === 'faceid'
      ? {
          kind: 'expanded',
          amount: formatAmount(txn.amount),
          counterparty: txn.counterparty,
          specterGrade: txn.specterGrade,
          approverIndex,
          approverTotal: approversRequired,
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
          : stage === 'flashing'
            ? latestEmotion?.family === 'coerced' || duress
              ? { kind: 'coerced', reason: latestEmotion?.label ?? 'coerced' }
              : { kind: 'vouched', emotion: latestEmotion?.label ?? 'neutral', cadence: 'ok' }
            : {
                kind: 'compact',
                amount: formatAmount(txn.amount),
                tier: txn.tier as 1 | 2 | 3,
              };

  const lastVouchOk = recordings.length > 0 && recordings[recordings.length - 1].vouched;
  const blocked = recordings.some((r) => !r.vouched);

  return (
    <BloomGradient>
      <DynamicIslandBanner
        state={islandState}
        captureRef={captureRef as React.RefObject<MediaCaptureHandle>}
        onCaptureError={(msg) => setBiometricError(msg)}
      />

      {/* Flash transition banner */}
      {flashMessage && (
        <View
          style={[
            styles.flashContainer,
            { top: insets.top + 100 },
            blocked && { borderColor: colors.pulseRed, backgroundColor: 'rgba(40,0,0,0.8)' },
          ]}
          pointerEvents="none"
        >
          <Text style={[styles.flashText, blocked && { color: colors.pulseRed }]}>
            {flashMessage}
          </Text>
        </View>
      )}

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{
          paddingTop: insets.top + 86,
          paddingBottom: insets.bottom + 80,
        }}
      >
        <View style={styles.headerBlock}>
          <Text style={styles.tier3Label}>TIER 3 · BIOMETRIC VOUCH</Text>
          <Pressable
            onPress={() => router.replace('/')}
            style={({ pressed }) => [styles.closeButton, pressed && { opacity: 0.55 }]}
            hitSlop={12}
          >
            <Text style={styles.closeButtonText}>✕</Text>
          </Pressable>
        </View>

        <SummaryCard txn={txn} approverIndex={approverIndex} approversRequired={approversRequired} recordings={recordings} />

        {/* Per-approver progress + playback list */}
        <View style={styles.approverList}>
          {Array.from({ length: approversRequired }).map((_, idx) => {
            const i = idx + 1;
            const isRemote = i > 1;
            const recording = recordings.find((r) => r.approverIndex === i);
            if (recording) {
              return (
                <ApproverPlayback
                  key={i}
                  recording={recording}
                  remoteApprover={isRemote ? REMOTE_APPROVER : undefined}
                />
              );
            }
            const active = i === approverIndex;
            const awaitingRemote = active && isRemote && stage === 'awaiting_remote';
            const label = !active
              ? `APPROVER ${i} · LOCKED`
              : awaitingRemote
                ? `APPROVER ${i} · ${REMOTE_APPROVER.name.toUpperCase()} · ${REMOTE_APPROVER.device.toUpperCase()}`
                : isRemote
                  ? `APPROVER ${i} · NOTIFYING ${REMOTE_APPROVER.name.toUpperCase()}`
                  : `APPROVER ${i} · AWAITING BIOMETRIC`;
            return (
              <View
                key={i}
                style={[
                  styles.pendingApprover,
                  active && styles.pendingApproverActive,
                  awaitingRemote && styles.pendingApproverRemote,
                ]}
              >
                <Text
                  style={[
                    styles.pendingApproverText,
                    active && { color: colors.accentAmber },
                  ]}
                >
                  {label}
                </Text>
                {awaitingRemote && (
                  <Text style={styles.remoteSubtext}>
                    push notification sent · awaiting biometric on {REMOTE_APPROVER.device.toLowerCase()}
                  </Text>
                )}
              </View>
            );
          })}
        </View>

        {/* Hint when expanded and last vouch was good */}
        {stage === 'expanded' && lastVouchOk && approverIndex <= approversRequired && (
          <Text style={styles.continueHint}>
            tap <Text style={styles.continueHintAmber}>Face ID</Text> in the island to continue with approver {approverIndex}
          </Text>
        )}

        {biometricError && (
          <Text style={styles.errorLine}>{biometricError}</Text>
        )}

        {classifierLoading && stage === 'expanded' && approverIndex === 1 && (
          <Text style={styles.classifierLine}>warming voice classifier…</Text>
        )}
      </ScrollView>

      <View style={[styles.devRow, { paddingBottom: insets.bottom + 12 }]}>
        <Pressable
          onPress={() => router.replace('/')}
          style={({ pressed }) => [styles.backToLedger, pressed && { opacity: 0.6 }]}
        >
          <Text style={styles.backToLedgerText}>← BACK TO LEDGER</Text>
        </Pressable>
        <View style={{ flex: 1 }} />
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

function SummaryCard({
  txn,
  approverIndex,
  approversRequired,
  recordings,
}: {
  txn: Transaction;
  approverIndex: number;
  approversRequired: number;
  recordings: ApproverRecording[];
}) {
  const formatAmount = (amount: number) =>
    `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;
  return (
    <View style={styles.summaryCard}>
      <View style={styles.summaryHeader}>
        <LogoAvatar
          name={txn.counterparty}
          domain={txn.domain}
          logoUrl={txn.logoUrl}
          brandColor={txn.brandColor}
          size={42}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.summaryCounterparty}>{txn.counterparty}</Text>
          <Text style={styles.summaryCategory}>{txn.category}</Text>
        </View>
        <View style={styles.tierPill}>
          <Text style={styles.tierPillText}>T{txn.tier}</Text>
        </View>
      </View>
      <Text style={styles.summaryAmount}>{formatAmount(txn.amount)}</Text>
      <View style={styles.summaryDivider} />
      <View style={styles.summaryGrid}>
        <View style={{ flex: 1 }}>
          <Text style={styles.summaryLabel}>REFERENCE</Text>
          <Text style={styles.summaryValue}>{txn.reference ?? '—'}</Text>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={styles.summaryLabel}>VOUCHES</Text>
          <Text style={styles.summaryValue}>
            {recordings.filter((r) => r.vouched).length} / {approversRequired}
          </Text>
        </View>
      </View>
      <View style={styles.summaryGrid}>
        <View style={{ flex: 1 }}>
          <Text style={styles.summaryLabel}>METHOD</Text>
          <Text style={styles.summaryValue}>{txn.method ?? 'Plaid · CHAPS'}</Text>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={styles.summaryLabel}>STATUS</Text>
          <Text style={[styles.summaryValue, { color: colors.pulseRed }]}>HOLDING</Text>
        </View>
      </View>
      {txn.specterNote && (
        <>
          <View style={styles.summaryDivider} />
          <Text style={styles.specterNote}>
            <Text style={{ color: colors.accentAmber }}>●● Specter {txn.specterGrade}</Text>{' '}
            · {txn.specterNote}
          </Text>
        </>
      )}
    </View>
  );
}

function amountWords(amount: number): string {
  if (amount === 62000) return 'sixty-two thousand';
  if (amount === 14000) return 'fourteen thousand';
  if (amount === 8400) return 'eight thousand four hundred';
  if (amount >= 1000) return `${(amount / 1000).toFixed(0)} thousand`;
  return `${amount}`;
}

const styles = StyleSheet.create({
  headerBlock: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 22,
    marginBottom: 18,
  },
  tier3Label: {
    ...type.caption,
    color: colors.pulseRed,
  },
  back: {
    color: colors.inkMono,
    fontSize: 18,
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.inkMono,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  closeButtonText: {
    color: colors.inkPrimary,
    fontSize: 16,
    fontWeight: '600',
  },
  summaryCard: {
    marginHorizontal: 16,
    backgroundColor: colors.cardFill,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    padding: 18,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.5,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 18 },
    elevation: 12,
    marginBottom: 16,
  },
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  summaryCounterparty: {
    fontFamily: type.body.fontFamily,
    fontSize: 16,
    fontWeight: '600',
    color: colors.cardInkPrimary,
  },
  summaryCategory: {
    ...type.caption,
    color: colors.cardInkSecondary,
    fontSize: 10,
  },
  tierPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.pulseRed,
    backgroundColor: 'rgba(255,59,48,0.12)',
  },
  tierPillText: {
    ...type.caption,
    color: colors.pulseRed,
    fontSize: 10,
    fontWeight: '700',
  },
  summaryAmount: {
    fontFamily: type.amountHero.fontFamily,
    fontSize: 44,
    color: colors.cardInkPrimary,
    letterSpacing: -0.5,
  },
  summaryDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.cardStroke,
  },
  summaryGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 16,
  },
  summaryLabel: {
    ...type.caption,
    color: colors.cardInkMuted,
    fontSize: 9.5,
    marginBottom: 3,
  },
  summaryValue: {
    fontFamily: type.body.fontFamily,
    fontSize: 12,
    fontWeight: '500',
    color: colors.cardInkPrimary,
  },
  specterNote: {
    fontFamily: type.body.fontFamily,
    fontSize: 11,
    color: colors.cardInkSecondary,
    lineHeight: 15,
  },
  approverList: {
    paddingHorizontal: 16,
    gap: 12,
  },
  pendingApprover: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.cardStroke,
    backgroundColor: 'rgba(0,0,0,0.32)',
  },
  pendingApproverActive: {
    borderColor: colors.accentAmber,
    backgroundColor: 'rgba(255,138,46,0.08)',
  },
  pendingApproverRemote: {
    borderColor: '#3FA9FF',
    backgroundColor: 'rgba(63,169,255,0.08)',
  },
  pendingApproverText: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 10.5,
  },
  remoteSubtext: {
    ...type.caption,
    fontSize: 9,
    color: colors.inkMono,
    marginTop: 6,
    textTransform: 'none',
    letterSpacing: 0.2,
  },
  continueHint: {
    ...type.body,
    color: colors.inkMono,
    textAlign: 'center',
    marginTop: 14,
    paddingHorizontal: 32,
    fontSize: 13,
  },
  continueHintAmber: {
    color: colors.accentAmber,
  },
  errorLine: {
    ...type.caption,
    color: colors.pulseRed,
    textAlign: 'center',
    marginTop: 8,
  },
  classifierLine: {
    ...type.caption,
    color: colors.accentAmber,
    fontSize: 10,
    textAlign: 'center',
    marginTop: 8,
  },
  flashContainer: {
    position: 'absolute',
    left: 24,
    right: 24,
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: 'rgba(0,30,10,0.85)',
    borderWidth: 1,
    borderColor: '#3FE07D',
    zIndex: 200,
    alignItems: 'center',
  },
  flashText: {
    ...type.caption,
    color: '#3FE07D',
    fontSize: 12,
    letterSpacing: 1.4,
    textAlign: 'center',
    fontWeight: '700',
  },
  devRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  devLabel: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 9,
    marginRight: 8,
  },
  backToLedger: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.accentAmber,
    backgroundColor: 'rgba(255,138,46,0.12)',
  },
  backToLedgerText: {
    ...type.caption,
    color: colors.accentAmber,
    fontSize: 10,
    fontWeight: '700',
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
