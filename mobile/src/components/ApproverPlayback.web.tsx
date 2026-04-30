import { colors } from '@/tokens/colors';

export interface ApproverRecording {
  approverIndex: number;
  videoUrl: string;
  vouched: boolean;
  emotionLabel: string;
  emotionScore: number;
  capturedAt: Date;
  durationSec: number;
  reason?: string;
}

interface ApproverPlaybackProps {
  recording: ApproverRecording;
}

export function ApproverPlayback({ recording }: ApproverPlaybackProps) {
  const accent = recording.vouched ? '#3FE07D' : colors.pulseRed;
  const status = recording.vouched ? 'VOUCHED' : 'COERCED · BLOCKED';

  return (
    <div
      style={{
        backgroundColor: colors.cardFill,
        borderRadius: 18,
        borderWidth: 1,
        borderStyle: 'solid',
        borderColor: recording.vouched ? colors.cardStroke : colors.pulseRed,
        padding: 14,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        boxShadow: '0 18px 32px rgba(0,0,0,0.55)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontFamily: 'Menlo, monospace',
            fontSize: 11,
            letterSpacing: 1.2,
            color: accent,
            fontWeight: 700,
          }}
        >
          APPROVER {recording.approverIndex} · {status}
        </div>
        <div
          style={{
            fontFamily: 'Menlo, monospace',
            fontSize: 10,
            color: colors.cardInkMuted,
          }}
        >
          {recording.capturedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
      </div>

      <video
        src={recording.videoUrl}
        controls
        playsInline
        muted={false}
        style={{
          width: '100%',
          aspectRatio: '0.78',
          borderRadius: 12,
          backgroundColor: '#000',
          objectFit: 'cover',
          transform: 'scaleX(-1)',
        }}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          fontFamily: 'Menlo, monospace',
          fontSize: 10,
          color: colors.cardInkSecondary,
        }}
      >
        <div>
          <div style={{ color: colors.cardInkMuted, fontSize: 9, letterSpacing: 1, marginBottom: 2 }}>
            EMOTION
          </div>
          <div style={{ color: accent, fontWeight: 600 }}>
            {recording.emotionLabel} · {(recording.emotionScore * 100).toFixed(0)}%
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: colors.cardInkMuted, fontSize: 9, letterSpacing: 1, marginBottom: 2 }}>
            DURATION
          </div>
          <div style={{ color: colors.cardInkPrimary }}>{recording.durationSec.toFixed(1)}s</div>
        </div>
      </div>

      {recording.reason && (
        <div
          style={{
            fontFamily: 'Menlo, monospace',
            fontSize: 10,
            color: colors.pulseRed,
            opacity: 0.85,
          }}
        >
          ▲ {recording.reason}
        </div>
      )}
    </div>
  );
}
