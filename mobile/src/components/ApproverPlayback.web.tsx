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

interface RemoteApprover {
  name: string;
  role: string;
  device: string;
}

interface ApproverPlaybackProps {
  recording: ApproverRecording;
  remoteApprover?: RemoteApprover;
}

export function ApproverPlayback({ recording, remoteApprover }: ApproverPlaybackProps) {
  const accent = recording.vouched ? '#3FE07D' : colors.pulseRed;
  const status = recording.vouched ? 'VOUCHED' : 'COERCED · BLOCKED';
  const isRemote = !recording.videoUrl && !!remoteApprover;

  if (isRemote) {
    return (
      <div
        style={{
          backgroundColor: colors.cardFill,
          borderRadius: 18,
          borderWidth: 1,
          borderStyle: 'solid',
          borderColor: '#3FA9FF',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
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
              color: '#3FA9FF',
              fontWeight: 700,
            }}
          >
            APPROVER {recording.approverIndex} · REMOTE VOUCH ✓
          </div>
          <div
            style={{
              fontFamily: 'Menlo, monospace',
              fontSize: 10,
              color: colors.cardInkMuted,
            }}
          >
            {recording.capturedAt.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            paddingTop: 8,
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 22,
              backgroundColor: '#3FA9FF',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: 'Menlo, monospace',
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {remoteApprover.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
          </div>
          <div style={{ flex: 1, fontFamily: 'Menlo, monospace' }}>
            <div style={{ color: colors.cardInkPrimary, fontSize: 14, fontWeight: 600 }}>
              {remoteApprover.name}
            </div>
            <div style={{ color: colors.cardInkSecondary, fontSize: 11 }}>
              {remoteApprover.role} · {remoteApprover.device}
            </div>
          </div>
          <div
            style={{
              fontFamily: 'Menlo, monospace',
              fontSize: 10,
              color: colors.cardInkMuted,
              textAlign: 'right',
            }}
          >
            <div style={{ marginBottom: 2 }}>VOUCHED</div>
            <div style={{ color: '#3FE07D', fontWeight: 700 }}>off-device</div>
          </div>
        </div>

        <div
          style={{
            fontFamily: 'Menlo, monospace',
            fontSize: 10,
            color: colors.cardInkMuted,
            paddingTop: 8,
            borderTop: `1px solid ${colors.cardStroke}`,
          }}
        >
          attestation captured on {remoteApprover.name}'s {remoteApprover.device.toLowerCase()} ·
          biometric + voice verified · receipt synced
        </div>
      </div>
    );
  }

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
