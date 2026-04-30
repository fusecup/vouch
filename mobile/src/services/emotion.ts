// Native stub. The web bundle resolves to emotion.web.ts; this module is the
// fallback for iOS/Android and currently returns 'unknown' until we wire
// up an on-device or backend classifier as part of the prebuild work.

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

export function isClassifierReady() {
  return false;
}

export function preloadEmotionClassifier() {
  return Promise.resolve(null);
}

export async function classifyAudio(_blob: Blob): Promise<EmotionResult> {
  return { label: 'unknown', score: 0, family: 'unknown' };
}
