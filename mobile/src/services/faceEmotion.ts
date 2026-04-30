// Native stub. Web bundle resolves to faceEmotion.web.ts. iOS/Android will
// route the same call to a Django/Cursor SDK backend post-prebuild.

export interface FaceEmotionResult {
  label: string;
  family: 'calm' | 'coerced' | 'unknown';
  confidence: number;
  rationale?: string;
}

export async function classifyFaceFrame(_dataUrl: string): Promise<FaceEmotionResult | null> {
  return null;
}
