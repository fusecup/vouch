// Web-side face emotion analyser. Sends a snapshot of the live webcam to
// Google's Gemini multimodal model and parses the structured response back
// into a coerced/calm decision. Hackathon key — replace before any real ship.

import { Platform } from 'react-native';

const GEMINI_API_KEY =
  process.env.EXPO_PUBLIC_GEMINI_API_KEY ?? 'AIzaSyBScZLEJlyT_3wIp0NGG4oPkrSTGN5a-dk';
const GEMINI_MODEL = 'gemini-2.0-flash';

export interface FaceEmotionResult {
  label: string;
  family: 'calm' | 'coerced' | 'unknown';
  confidence: number;
  rationale?: string;
}

const COERCED = new Set(['stressed', 'fearful', 'fear', 'distressed', 'tense', 'forced', 'coerced']);
const CALM = new Set(['neutral', 'calm', 'composed', 'relaxed', 'happy', 'confident', 'attentive']);

function classify(label: string): 'calm' | 'coerced' | 'unknown' {
  const l = label.toLowerCase().trim();
  if (COERCED.has(l)) return 'coerced';
  if (CALM.has(l)) return 'calm';
  return 'unknown';
}

const PROMPT = `You are a coercion-detection model auxiliary to a financial vouching system.
Look at the person's facial expression in this single frame and decide whether they appear to
be giving a free, attentive, calm attestation, OR whether they show signs of distress,
fear, coercion, or forced cooperation.

Respond with strictly the JSON shape:
{"label": <string>, "confidence": <0-1>, "rationale": <one short sentence>}

Allowed labels: neutral, calm, composed, attentive, stressed, fearful, distressed, coerced.
Lean toward stressed/fearful/coerced if you see micro-tension, asymmetric eye widening,
forced jaw tension, or eye darting. Otherwise neutral/calm/composed/attentive.`;

export async function classifyFaceFrame(dataUrl: string): Promise<FaceEmotionResult | null> {
  if (Platform.OS !== 'web') return null;
  if (!dataUrl || !dataUrl.startsWith('data:')) return null;

  const commaIdx = dataUrl.indexOf(',');
  if (commaIdx < 0) return null;
  const base64 = dataUrl.slice(commaIdx + 1);
  const mimeMatch = /^data:([^;]+);base64/.exec(dataUrl);
  const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
  const body = {
    contents: [
      {
        parts: [
          { text: PROMPT },
          { inline_data: { mime_type: mime, data: base64 } },
        ],
      },
    ],
    generationConfig: {
      temperature: 0.1,
      response_mime_type: 'application/json',
    },
  };

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      // 4xx/5xx — treat as unknown so the demo doesn't break
      return null;
    }
    const json = await res.json();
    const text = json?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text || typeof text !== 'string') return null;

    let parsed: { label?: string; confidence?: number; rationale?: string };
    try {
      parsed = JSON.parse(text);
    } catch {
      // Fallback — attempt a label-only parse from the first line
      const first = text.split('\n')[0]?.trim() ?? '';
      parsed = { label: first, confidence: 0.6 };
    }

    const label = (parsed.label ?? 'unknown').toString();
    const confidence = typeof parsed.confidence === 'number' ? Math.max(0, Math.min(1, parsed.confidence)) : 0.6;

    return {
      label,
      family: classify(label),
      confidence,
      rationale: parsed.rationale,
    };
  } catch {
    return null;
  }
}
