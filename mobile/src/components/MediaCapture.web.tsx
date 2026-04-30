import { forwardRef, useImperativeHandle, useRef, useState } from 'react';

import { colors } from '@/tokens/colors';

export interface MediaCaptureHandle {
  start: () => Promise<void>;
  stop: () => Promise<{ audioBlob: Blob; mimeType: string }>;
  cancel: () => void;
}

interface MediaCaptureProps {
  onError?: (msg: string) => void;
}

export const MediaCapture = forwardRef<MediaCaptureHandle, MediaCaptureProps>(
  ({ onError }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const recorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const [active, setActive] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const cleanup = () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      recorderRef.current = null;
      setActive(false);
    };

    useImperativeHandle(ref, () => ({
      async start() {
        setError(null);
        try {
          if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error('mediaDevices.getUserMedia unavailable in this browser');
          }
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 720 }, height: { ideal: 960 }, facingMode: 'user' },
            audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 48000 },
          });
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play().catch(() => {});
          }

          const audioStream = new MediaStream(stream.getAudioTracks());
          const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
              ? 'audio/webm'
              : MediaRecorder.isTypeSupported('audio/mp4')
                ? 'audio/mp4'
                : '';
          const recorder = mime ? new MediaRecorder(audioStream, { mimeType: mime }) : new MediaRecorder(audioStream);
          chunksRef.current = [];
          recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
          };
          recorder.start(250);
          recorderRef.current = recorder;
          setActive(true);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          setError(msg);
          onError?.(msg);
          cleanup();
          throw e;
        }
      },

      stop() {
        return new Promise((resolve) => {
          const recorder = recorderRef.current;
          if (!recorder || recorder.state === 'inactive') {
            const blob = new Blob(chunksRef.current, { type: recorder?.mimeType ?? 'audio/webm' });
            cleanup();
            resolve({ audioBlob: blob, mimeType: blob.type });
            return;
          }
          recorder.onstop = () => {
            const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
            cleanup();
            resolve({ audioBlob: blob, mimeType: recorder.mimeType });
          };
          try {
            recorder.stop();
          } catch {
            cleanup();
            resolve({ audioBlob: new Blob(chunksRef.current), mimeType: 'audio/webm' });
          }
        });
      },

      cancel() {
        try {
          recorderRef.current?.stop();
        } catch {
          /* ignore */
        }
        cleanup();
      },
    }));

    return (
      <div
        style={{
          width: '100%',
          aspectRatio: '0.72',
          borderRadius: 14,
          backgroundColor: '#0A0604',
          borderWidth: 1,
          borderStyle: 'solid',
          borderColor: colors.cardStroke,
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: 'scaleX(-1)',
          }}
        />
        {!active && !error && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: colors.inkMuted,
              fontFamily: 'Menlo, monospace',
              fontSize: 11,
              letterSpacing: 1,
            }}
          >
            CAMERA STANDBY
          </div>
        )}
        {error && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: colors.pulseRed,
              fontFamily: 'Menlo, monospace',
              fontSize: 11,
              letterSpacing: 1,
              textAlign: 'center',
              padding: 18,
            }}
          >
            CAMERA / MIC DENIED
            <span style={{ marginTop: 8, color: colors.inkMono, opacity: 0.7 }}>{error}</span>
          </div>
        )}
        {active && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              right: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'Menlo, monospace',
              fontSize: 10,
              letterSpacing: 1,
              color: colors.pulseRed,
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 4,
                backgroundColor: colors.pulseRed,
                boxShadow: '0 0 8px rgba(255,59,48,0.9)',
              }}
            />
            REC
          </div>
        )}
      </div>
    );
  },
);

MediaCapture.displayName = 'MediaCapture';
