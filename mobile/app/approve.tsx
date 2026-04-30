import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BloomGradient } from '@/components/BloomGradient';
import { PulseDot } from '@/components/PulseDot';
import { TinderCard } from '@/components/TinderCard';
import { pendingTransactions } from '@/data/mockTransactions';
import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';
import { Transaction } from '@/types/transaction';

export default function ApproveScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ id?: string }>();

  const [decisions, setDecisions] = useState<Record<string, 'approved' | 'rejected' | 'escalated'>>({});

  const queue = useMemo(() => {
    const tier2 = pendingTransactions.filter((t) => t.tier === 2);
    if (params.id) {
      const head = pendingTransactions.find((t) => t.id === params.id && t.tier === 2);
      if (head) return [head, ...tier2.filter((t) => t.id !== head.id)];
    }
    return tier2;
  }, [params.id]);

  const remaining = queue.filter((t) => !decisions[t.id]);
  const current = remaining[0];

  const handleApprove = (txn: Transaction) => setDecisions((d) => ({ ...d, [txn.id]: 'approved' }));
  const handleReject = (txn: Transaction) => setDecisions((d) => ({ ...d, [txn.id]: 'rejected' }));
  const handleEscalate = (txn: Transaction) => {
    setDecisions((d) => ({ ...d, [txn.id]: 'escalated' }));
    router.replace({ pathname: '/vouch', params: { id: txn.id } });
  };

  return (
    <BloomGradient>
      <View style={[styles.header, { paddingTop: insets.top + 14 }]}>
        <View style={styles.headerLeft}>
          <PulseDot size={7} />
          <Text style={styles.headerLabel}>LIVE</Text>
        </View>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.back}>←</Text>
        </Pressable>
      </View>

      <View style={styles.cardArea}>
        {current ? (
          <TinderCard
            key={current.id}
            txn={current}
            onApprove={handleApprove}
            onReject={handleReject}
            onEscalate={handleEscalate}
          />
        ) : (
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>INBOX CLEAR</Text>
            <Text style={styles.emptyBody}>
              {Object.keys(decisions).length} processed · {Object.values(decisions).filter(d => d === 'approved').length} approved · {Object.values(decisions).filter(d => d === 'rejected').length} rejected
            </Text>
            <Pressable style={styles.doneButton} onPress={() => router.replace('/')}>
              <Text style={styles.doneText}>BACK TO LEDGER</Text>
            </Pressable>
          </View>
        )}
      </View>

      <View style={[styles.actionsRow, { paddingBottom: insets.bottom + 36 }]}>
        <ActionGlyph
          label="reject"
          glyph="✕"
          color={colors.pulseRed}
          onPress={current ? () => handleReject(current) : undefined}
        />
        <ActionGlyph
          label="escalate"
          glyph="↑"
          color={colors.accentAmber}
          onPress={current ? () => handleEscalate(current) : undefined}
        />
        <ActionGlyph
          label="approve"
          glyph="✓"
          color="#3FE07D"
          onPress={current ? () => handleApprove(current) : undefined}
        />
      </View>
    </BloomGradient>
  );
}

function ActionGlyph({
  label,
  glyph,
  color,
  onPress,
}: {
  label: string;
  glyph: string;
  color: string;
  onPress?: () => void;
}) {
  return (
    <Pressable
      style={({ pressed }) => [styles.actionItem, pressed && { opacity: 0.6 }]}
      onPress={onPress}
      disabled={!onPress}
    >
      <View style={[styles.glyphCircle, { borderColor: color }]}>
        <Text style={[styles.glyphText, { color }]}>{glyph}</Text>
      </View>
      <Text style={styles.actionLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerLabel: {
    ...type.caption,
    color: colors.pulseRed,
  },
  back: {
    color: colors.inkMono,
    fontSize: 22,
  },
  cardArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  empty: {
    alignItems: 'center',
    gap: 16,
  },
  emptyTitle: {
    ...type.caption,
    color: colors.inkMono,
    fontSize: 14,
  },
  emptyBody: {
    ...type.body,
    color: colors.inkMono,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  doneButton: {
    marginTop: 24,
    paddingHorizontal: 22,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.accentAmber,
  },
  doneText: {
    ...type.caption,
    color: colors.accentAmber,
  },
  actionsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 18,
  },
  actionItem: {
    alignItems: 'center',
    gap: 8,
  },
  glyphCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  glyphText: {
    fontSize: 22,
    fontWeight: '600',
  },
  actionLabel: {
    ...type.caption,
    color: colors.inkMono,
    fontSize: 10,
  },
});
