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

type Pipe = (input: Float32Array, opts?: { topk?: number }) => Promise<Array<{ label: string; score: number }>>;

let classifierPromise: Promise<Pipe> | null = null;
let classifierReady = false;

export function isClassifierReady() {
  return classifierReady;
}

export function preloadEmotionClassifier(): Promise<Pipe | null> {
  if (Platform.OS !== 'web') return Promise.resolve(null);
  if (classifierPromise) return classifierPromise;

  classifierPromise = (async () => {
    const tf = await import('@huggingface/transformers');
    tf.env.allowLocalModels = false;
    const pipe = (await tf.pipeline(
      'audio-classification',
      'Xenova/wav2vec2-base-superb-er',
      { dtype: 'fp32' },
    )) as unknown as Pipe;
    classifierReady = true;
    return pipe;
  })();

  return classifierPromise;
}

const COERCED_LABELS = new Set(['ang', 'angry', 'sad', 'fearful', 'fear']);
const CALM_LABELS = new Set(['neu', 'neutral', 'happy', 'hap', 'calm']);

function classify(label: string): 'calm' | 'coerced' | 'unknown' {
  const l = label.toLowerCase();
  if (COERCED_LABELS.has(l)) return 'coerced';
  if (CALM_LABELS.has(l)) return 'calm';
  return 'unknown';
}

async function decodeToFloat32(blob: Blob, targetSampleRate = 16000): Promise<{ samples: Float32Array; durationSec: number }> {
  const arrayBuffer = await blob.arrayBuffer();
  const Ctx = (window as unknown as { AudioContext: typeof AudioContext; webkitAudioContext?: typeof AudioContext })
    .AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
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
  const rmsVar =
    rmsValues.length > 0
      ? rmsValues.reduce((acc, v) => acc + (v - rmsMean) ** 2, 0) / rmsValues.length
      : 0;
  const durationSec = samples.length / sampleRate;
  const syllableRate = voicedFrames > 0 ? voicedFrames / 100 / durationSec : 0;

  // Crude spectral centroid estimate via zero-crossing rate proxy
  let zc = 0;
  for (let i = 1; i < samples.length; i += 1) {
    if ((samples[i - 1] >= 0 && samples[i] < 0) || (samples[i - 1] < 0 && samples[i] >= 0)) zc += 1;
  }
  const spectralCentroid = (zc / samples.length) * sampleRate * 0.5;

  return { durationSec, rmsMean, rmsVariance: rmsVar, spectralCentroid, syllableRate };
}

function heuristicLabel(features: ReturnType<typeof computeFeatures>): EmotionResult {
  const { rmsVariance, spectralCentroid, syllableRate } = features;
  // Heuristics — rushed cadence + high spectral content suggests stress
  let label = 'neutral';
  let family: 'calm' | 'coerced' | 'unknown' = 'calm';
  let score = 0.6;

  if (syllableRate > 5.5 || rmsVariance > 0.012) {
    label = 'rushed';
    family = 'coerced';
    score = Math.min(0.95, 0.6 + rmsVariance * 20 + (syllableRate - 5.5) * 0.05);
  } else if (spectralCentroid > 3500 && rmsVariance > 0.006) {
    label = 'stressed';
    family = 'coerced';
    score = 0.78;
  }
  return { label, score, family, features };
}

export async function classifyAudio(blob: Blob): Promise<EmotionResult> {
  if (Platform.OS !== 'web') {
    return { label: 'unknown', score: 0, family: 'unknown' };
  }

  const { samples, durationSec } = await decodeToFloat32(blob, 16000);
  const features = computeFeatures(samples, 16000);

  // Try the real classifier; fall back to heuristic if unavailable
  try {
    const classifier = await preloadEmotionClassifier();
    if (!classifier) throw new Error('classifier unavailable');
    const results = await classifier(samples, { topk: 4 });
    if (results && results.length > 0) {
      const top = results[0];
      return {
        label: top.label,
        score: top.score,
        family: classify(top.label),
        features: { ...features, durationSec },
      };
    }
  } catch {
    /* fall through to heuristic */
  }

  return heuristicLabel(features);
}
