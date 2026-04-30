import * as LocalAuthentication from 'expo-local-authentication';
import { Platform } from 'react-native';

export type BiometricResult =
  | { ok: true; method: 'face' | 'fingerprint' | 'webauthn' | 'simulated' }
  | { ok: false; reason: 'cancelled' | 'unavailable' | 'failed' | 'no_hardware' };

/**
 * Web: triggers the platform authenticator via WebAuthn — on macOS this is Touch ID,
 * on Windows it's Windows Hello, on iOS Safari it's Face ID. We don't actually verify
 * the credential server-side; we just need the user to complete the biometric.
 */
async function webPrompt(): Promise<BiometricResult> {
  if (typeof window === 'undefined' || !('PublicKeyCredential' in window)) {
    return { ok: false, reason: 'unavailable' };
  }

  try {
    const available = await (
      window as unknown as { PublicKeyCredential: { isUserVerifyingPlatformAuthenticatorAvailable?: () => Promise<boolean> } }
    ).PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable?.();
    if (available === false) return { ok: false, reason: 'no_hardware' };
  } catch {
    /* fall through to attempt creation */
  }

  const challenge = new Uint8Array(32);
  crypto.getRandomValues(challenge);
  const userId = new Uint8Array(16);
  crypto.getRandomValues(userId);

  try {
    await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { name: 'Vouch' },
        user: {
          id: userId,
          name: `vouch-${Date.now()}`,
          displayName: 'Vouch Approver',
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 },
          { type: 'public-key', alg: -257 },
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'required',
          requireResidentKey: false,
        },
        timeout: 60000,
        attestation: 'none',
      },
    });
    return { ok: true, method: 'webauthn' };
  } catch (e: unknown) {
    const name = (e as { name?: string })?.name ?? '';
    if (name === 'NotAllowedError') return { ok: false, reason: 'cancelled' };
    return { ok: false, reason: 'failed' };
  }
}

async function nativePrompt(): Promise<BiometricResult> {
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  if (!hasHardware) return { ok: false, reason: 'no_hardware' };

  const enrolled = await LocalAuthentication.isEnrolledAsync();
  if (!enrolled) return { ok: false, reason: 'unavailable' };

  const supported = await LocalAuthentication.supportedAuthenticationTypesAsync();

  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Vouch authorization',
    fallbackLabel: 'Use passcode',
    disableDeviceFallback: false,
    cancelLabel: 'Cancel',
  });

  if (!result.success) {
    if ('error' in result && result.error === 'user_cancel') {
      return { ok: false, reason: 'cancelled' };
    }
    return { ok: false, reason: 'failed' };
  }

  const isFace = supported.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION);
  return { ok: true, method: isFace ? 'face' : 'fingerprint' };
}

export async function promptBiometric(): Promise<BiometricResult> {
  if (Platform.OS === 'web') return webPrompt();
  return nativePrompt();
}
