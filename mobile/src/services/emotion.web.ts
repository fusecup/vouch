// Web-side emotion classifier.
//
// The PRD calls for FunAudioLLM/SenseVoiceSmall + opencv/facial_expression_recognition
// running server-side via the Django agent (Member B). For the in-browser demo
// we run a lightweight DSP feature extractor on the captured audio and map the
// features to a coerced/calm decision. Real audio in, real signal processing,
// real classification — just much cheaper than loading a 100MB ONNX model into
// Metro's web bundle (which currently chokes on onnxruntime-web's dynamic imports).

import { Platform } from 'react-native';

export interface EmotionResult {
  label: string;
  score: number;
  family: 'calm' | 'coerced' | 'unknown';
  features?: {
    durationSec: number;
    rmsMean: number;
    rmsVariance: number;
    spectralCentroid: number;
    syllableRate: number;
  };
}

let ready = true;

export function isClassifierReady() {
  return ready;
}

export function preloadEmotionClassifier(): Promise<null> {
  ready = true;
  return Promise.resolve(null);
}

async function decodeToFloat32(
  blob: Blob,
  targetSampleRate = 16000,
): Promise<{ samples: Float32Array; durationSec: number }> {
  const arrayBuffer = await blob.arrayBuffer();
  const Ctx =
    (window as unknown as { AudioContext: typeof AudioContext }).AudioContext ??
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const audioCtx = new Ctx();
  const decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
  await audioCtx.close();

  const ch = decoded.numberOfChannels > 0 ? decoded.getChannelData(0) : new Float32Array();
  const ratio = decoded.sampleRate / targetSampleRate;
  if (Math.abs(ratio - 1) < 0.01) {
    return { samples: ch, durationSec: decoded.duration };
  }
  const newLength = Math.floor(ch.length / ratio);
  const out = new Float32Array(newLength);
  for (let i = 0; i < newLength; i += 1) {
    const idx = i * ratio;
    const lo = Math.floor(idx);
    const hi = Math.min(ch.length - 1, lo + 1);
    const frac = idx - lo;
    out[i] = ch[lo] * (1 - frac) + ch[hi] * frac;
  }
  return { samples: out, durationSec: decoded.duration };
}

function computeFeatures(samples: Float32Array, sampleRate = 16000) {
  const frameSize = 400; // 25ms @ 16kHz
  const hopSize = 160; // 10ms hop
  const rmsValues: number[] = [];
  let voicedFrames = 0;
  let totalEnergy = 0;
  for (let start = 0; start + frameSize <= samples.length; start += hopSize) {
    let sum = 0;
    for (let i = 0; i < frameSize; i += 1) {
      const v = samples[start + i];
      sum += v * v;
    }
    const rms = Math.sqrt(sum / frameSize);
    rmsValues.push(rms);
    totalEnergy += rms;
    if (rms > 0.02) voicedFrames += 1;
  }
  const rmsMean = rmsValues.length > 0 ? totalEnergy / rmsValues.length : 0;
  const rmsVariance =
    rmsValues.length > 0
      ? rmsValues.reduce((acc, v) => acc + (v - rmsMean) ** 2, 0) / rmsValues.length
      : 0;
  const durationSec = samples.length / sampleRate;
  const syllableRate = durationSec > 0 ? voicedFrames / 100 / durationSec : 0;

  // Zero-crossing rate as a cheap proxy for spectral centroid.
  let zc = 0;
  for (let i = 1; i < samples.length; i += 1) {
    if ((samples[i - 1] >= 0 && samples[i] < 0) || (samples[i - 1] < 0 && samples[i] >= 0)) zc += 1;
  }
  const spectralCentroid =
    samples.length > 0 ? (zc / samples.length) * sampleRate * 0.5 : 0;

  return { durationSec, rmsMean, rmsVariance, spectralCentroid, syllableRate };
}

export async function classifyAudio(blob: Blob): Promise<EmotionResult> {
  if (Platform.OS !== 'web') {
    return { label: 'unknown', score: 0, family: 'unknown' };
  }

  if (!blob || blob.size === 0) {
    return { label: 'no audio', score: 0, family: 'unknown' };
  }

  const { samples, durationSec } = await decodeToFloat32(blob, 16000);
  const features = computeFeatures(samples, 16000);

  // Heuristic decision tree. Tuned on a few sample voices; thresholds err
  // on the safe side because Tier 3 errs toward blocking.
  let label = 'neutral';
  let family: EmotionResult['family'] = 'calm';
  let score = 0.62;

  if (features.rmsMean < 0.005) {
    label = 'silence';
    family = 'unknown';
    score = 0.3;
  } else if (features.syllableRate > 5.5 || features.rmsVariance > 0.012) {
    label = 'rushed cadence';
    family = 'coerced';
    score = Math.min(
      0.95,
      0.6 + features.rmsVariance * 20 + Math.max(0, features.syllableRate - 5.5) * 0.05,
    );
  } else if (features.spectralCentroid > 3500 && features.rmsVariance > 0.006) {
    label = 'stressed';
    family = 'coerced';
    score = 0.78;
  } else if (features.rmsMean > 0.03 && features.rmsVariance < 0.004) {
    label = 'composed';
    family = 'calm';
    score = 0.82;
  }

  return {
    label,
    score,
    family,
    features: { ...features, durationSec },
  };
}
