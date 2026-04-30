import { Pressable, StyleSheet, View, Text } from 'react-native';

import { LogoAvatar } from '@/components/LogoAvatar';
import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';
import { Tier, Transaction } from '@/types/transaction';

interface TxnRowProps {
  txn: Transaction;
  onPress?: (txn: Transaction) => void;
}

const tierColor = (tier: Tier) => {
  if (tier === 1) return colors.tier0;
  if (tier === 2) return colors.tier1;
  return colors.tier2;
};

const formatAmount = (amount: number) =>
  `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

export function TxnRow({ txn, onPress }: TxnRowProps) {
  const accent = tierColor(txn.tier);
  const isAutoPaid = txn.status === 'auto_paid';
  const isTier3 = txn.tier === 3;

  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] }]}
      onPress={() => onPress?.(txn)}
    >
      <View style={styles.row}>
        <LogoAvatar
          name={txn.counterparty}
          domain={txn.domain}
          logoUrl={txn.logoUrl}
          brandColor={txn.brandColor}
          size={42}
        />

        <View style={styles.middle}>
          <View style={styles.titleRow}>
            <Text style={styles.counterparty} numberOfLines={1}>
              {txn.counterparty}
            </Text>
            <Text style={styles.amount}>{formatAmount(txn.amount)}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaPiece} numberOfLines={1}>
              {txn.dateLabel ?? '—'}
            </Text>
            <Text style={styles.metaDivider}>·</Text>
            <Text style={styles.metaPiece} numberOfLines={1}>
              {txn.recurring ? 'Recurring' : 'One-off'}
            </Text>
            <Text style={styles.metaDivider}>·</Text>
            <Text style={styles.metaPiece} numberOfLines={1}>
              {txn.timeToClear ?? '—'}
            </Text>
          </View>
        </View>
      </View>

      <View style={[styles.tierStrip, { backgroundColor: accent }]} />

      <View style={[styles.tierBadge, { borderColor: accent }]}>
        <Text style={[styles.tierBadgeText, { color: accent }]}>T{txn.tier}</Text>
        {isAutoPaid && <Text style={[styles.tierBadgeGlyph, { color: accent }]}>✓</Text>}
        {isTier3 && txn.status === 'pending' && (
          <Text style={[styles.tierBadgeGlyph, { color: accent }]}>▲</Text>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardFill,
    borderRadius: 16,
    paddingVertical: 14,
    paddingLeft: 18,
    paddingRight: 14,
    marginHorizontal: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.cardStroke,
    shadowColor: '#000',
    shadowOpacity: 0.45,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 14 },
    elevation: 8,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  middle: {
    flex: 1,
    gap: 4,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: 12,
  },
  counterparty: {
    flex: 1,
    fontFamily: type.body.fontFamily,
    fontSize: 16,
    fontWeight: '600',
    color: colors.cardInkPrimary,
  },
  amount: {
    fontFamily: type.amountList.fontFamily,
    fontSize: 22,
    fontWeight: '400',
    color: colors.cardInkPrimary,
    letterSpacing: -0.3,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaPiece: {
    fontFamily: type.body.fontFamily,
    fontSize: 11,
    color: colors.cardInkSecondary,
    letterSpacing: 0.1,
  },
  metaDivider: {
    fontFamily: type.body.fontFamily,
    fontSize: 11,
    color: colors.cardInkMuted,
  },
  tierStrip: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 3,
  },
  tierBadge: {
    position: 'absolute',
    right: 14,
    top: 12,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 5,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: 'rgba(255,253,248,0.6)',
  },
  tierBadgeText: {
    fontFamily: type.caption.fontFamily,
    fontSize: 9,
    letterSpacing: 0.8,
    fontWeight: '700',
  },
  tierBadgeGlyph: {
    fontSize: 9,
    fontWeight: '700',
  },
});
