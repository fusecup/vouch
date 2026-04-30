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
      style={({ pressed }) => [
        styles.row,
        isTier3 && { borderLeftColor: accent, borderLeftWidth: 2 },
        pressed && { opacity: 0.55 },
      ]}
      onPress={() => onPress?.(txn)}
    >
      <LogoAvatar
        name={txn.counterparty}
        domain={txn.domain}
        logoUrl={txn.logoUrl}
        brandColor={txn.brandColor}
        size={38}
      />

      <View style={styles.middle}>
        <Text style={styles.counterparty} numberOfLines={1}>
          {txn.counterparty}
        </Text>
        <Text style={styles.metaLine} numberOfLines={1}>
          {[txn.dateLabel, txn.recurring ? 'Recurring' : 'One-off', txn.timeToClear]
            .filter(Boolean)
            .join(' · ')}
        </Text>
      </View>

      <View style={styles.right}>
        <Text style={styles.amount}>{formatAmount(txn.amount)}</Text>
        <View style={styles.tierBlock}>
          <Text style={[styles.tierLabel, { color: accent }]}>TIER {txn.tier}</Text>
          {isAutoPaid && <Text style={[styles.glyph, { color: accent }]}>  ✓</Text>}
          {isTier3 && txn.status === 'pending' && (
            <Text style={[styles.glyph, { color: accent }]}>  ▲</Text>
          )}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 22,
    gap: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#1A1208',
  },
  middle: {
    flex: 1,
    gap: 3,
  },
  counterparty: {
    ...type.body,
    color: colors.inkPrimary,
    fontSize: 15,
    fontWeight: '500',
  },
  metaLine: {
    ...type.body,
    color: colors.inkMono,
    fontSize: 11,
    opacity: 0.8,
  },
  right: {
    alignItems: 'flex-end',
    gap: 4,
  },
  amount: {
    ...type.amountList,
    color: colors.inkPrimary,
    fontSize: 22,
  },
  tierBlock: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  tierLabel: {
    ...type.caption,
    fontSize: 9,
  },
  glyph: {
    ...type.caption,
    fontSize: 10,
  },
});
