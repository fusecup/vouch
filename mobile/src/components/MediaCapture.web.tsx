import { forwardRef, useImperativeHandle, useRef, useState } from 'react';

import { colors } from '@/tokens/colors';

export interface MediaCaptureHandle {
  start: () => Promise<void>;
  stop: () => Promise<{ audioBlob: Blob; videoBlob: Blob; mimeType: string }>;
  cancel: () => void;
  captureFrameDataUrl: () => string | null;
}

interface MediaCaptureProps {
  onError?: (msg: string) => void;
}

export const MediaCapture = forwardRef<MediaCaptureHandle, MediaCaptureProps>(
  ({ onError }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const audioRecorderRef = useRef<MediaRecorder | null>(null);
    const videoRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const videoChunksRef = useRef<Blob[]>([]);
    const [active, setActive] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const cleanup = () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      audioRecorderRef.current = null;
      videoRecorderRef.current = null;
      setActive(false);
    };

    useImperativeHandle(ref, () => ({
      async start() {
        setError(null);
        try {
          if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error('getUserMedia unavailable — needs https or localhost');
          }

          // Request video first so we always have a preview, then audio so
          // the user sees two distinct prompts and we can detect mic-denial
          // separately from camera-denial.
          const videoStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 720 }, height: { ideal: 960 }, facingMode: 'user' },
            audio: false,
          });

          let audioStream: MediaStream | null = null;
          try {
            audioStream = await navigator.mediaDevices.getUserMedia({
              audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 48000 },
              video: false,
            });
          } catch (audioErr) {
            videoStream.getTracks().forEach((t) => t.stop());
            const name = (audioErr as { name?: string })?.name ?? '';
            const reason =
              name === 'NotAllowedError'
                ? 'microphone permission denied'
                : name === 'NotFoundError'
                  ? 'no microphone found'
                  : 'microphone unavailable';
            throw new Error(reason);
          }

          // Combine into one stream so the preview shows the camera and we
          // record audio off the dedicated audio stream.
          const combined = new MediaStream([
            ...videoStream.getVideoTracks(),
            ...audioStream.getAudioTracks(),
          ]);
          streamRef.current = combined;

          if (videoRef.current) {
            videoRef.current.srcObject = combined;
            await videoRef.current.play().catch(() => {});
          }

          const audioOnly = new MediaStream(audioStream.getAudioTracks());
          if (audioOnly.getAudioTracks().length === 0) {
            throw new Error('no audio track captured');
          }

          // Audio recorder — for emotion classification.
          const audioMime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
              ? 'audio/webm'
              : MediaRecorder.isTypeSupported('audio/mp4')
                ? 'audio/mp4'
                : '';
          const audioRecorder = audioMime
            ? new MediaRecorder(audioOnly, { mimeType: audioMime })
            : new MediaRecorder(audioOnly);
          audioChunksRef.current = [];
          audioRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
          };
          audioRecorder.onerror = (e) => {
            const msg = (e as unknown as { error?: { message?: string } }).error?.message ?? 'audio recorder error';
            setError(msg);
            onError?.(msg);
          };
          audioRecorder.start(250);
          audioRecorderRef.current = audioRecorder;

          // Video recorder — for playback (combined video + audio).
          const videoMime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
            ? 'video/webm;codecs=vp9,opus'
            : MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
              ? 'video/webm;codecs=vp8,opus'
              : MediaRecorder.isTypeSupported('video/webm')
                ? 'video/webm'
                : MediaRecorder.isTypeSupported('video/mp4')
                  ? 'video/mp4'
                  : '';
          const videoRecorder = videoMime
            ? new MediaRecorder(combined, { mimeType: videoMime })
            : new MediaRecorder(combined);
          videoChunksRef.current = [];
          videoRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) videoChunksRef.current.push(e.data);
          };
          videoRecorder.onerror = (e) => {
            const msg = (e as unknown as { error?: { message?: string } }).error?.message ?? 'video recorder error';
            setError(msg);
            onError?.(msg);
          };
          videoRecorder.start(500);
          videoRecorderRef.current = videoRecorder;

          setActive(true);
        } catch (e) {
          const name = (e as { name?: string })?.name ?? '';
          const baseMsg = e instanceof Error ? e.message : String(e);
          const msg =
            name === 'NotAllowedError'
              ? 'camera/microphone permission denied'
              : name === 'NotFoundError'
                ? 'no camera or microphone found'
                : baseMsg;
          setError(msg);
          onError?.(msg);
          cleanup();
          throw new Error(msg);
        }
      },

      stop() {
        return new Promise((resolve) => {
          const audioRecorder = audioRecorderRef.current;
          const videoRecorder = videoRecorderRef.current;

          let audioDone = !audioRecorder || audioRecorder.state === 'inactive';
          let videoDone = !videoRecorder || videoRecorder.state === 'inactive';
          let audioBlob = new Blob(audioChunksRef.current, {
            type: audioRecorder?.mimeType ?? 'audio/webm',
          });
          let videoBlob = new Blob(videoChunksRef.current, {
            type: videoRecorder?.mimeType ?? 'video/webm',
          });

          const finalize = () => {
            if (!audioDone || !videoDone) return;
            cleanup();
            resolve({
              audioBlob,
              videoBlob,
              mimeType: videoBlob.type,
            });
          };

          if (audioRecorder && !audioDone) {
            audioRecorder.onstop = () => {
              audioBlob = new Blob(audioChunksRef.current, { type: audioRecorder.mimeType });
              audioDone = true;
              finalize();
            };
            try {
              audioRecorder.stop();
            } catch {
              audioDone = true;
              finalize();
            }
          }

          if (videoRecorder && !videoDone) {
            videoRecorder.onstop = () => {
              videoBlob = new Blob(videoChunksRef.current, { type: videoRecorder.mimeType });
              videoDone = true;
              finalize();
            };
            try {
              videoRecorder.stop();
            } catch {
              videoDone = true;
              finalize();
            }
          }

          if (audioDone && videoDone) finalize();
        });
      },

      cancel() {
        try {
          audioRecorderRef.current?.stop();
        } catch {
          /* ignore */
        }
        try {
          videoRecorderRef.current?.stop();
        } catch {
          /* ignore */
        }
        cleanup();
      },

      captureFrameDataUrl() {
        const video = videoRef.current;
        if (!video || video.videoWidth === 0) return null;
        const w = Math.min(640, video.videoWidth);
        const h = Math.round((video.videoHeight / video.videoWidth) * w);
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;
        // un-mirror — the preview is scaleX(-1), restore for downstream models
        ctx.translate(w, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, w, h);
        try {
          return canvas.toDataURL('image/jpeg', 0.8);
        } catch {
          return null;
        }
      },
    }));

    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: '#0A0604',
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
