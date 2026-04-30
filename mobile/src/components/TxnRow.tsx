import { Pressable, StyleSheet, View, Text } from 'react-native';

import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';
import { Tier, Transaction } from '@/types/transaction';

interface TxnRowProps {
  txn: Transaction;
  onPress?: (txn: Transaction) => void;
}

const tierLabel = (tier: Tier) => `TIER ${tier}`;
const tierColor = (tier: Tier) => {
  if (tier === 0) return colors.tier0;
  if (tier === 1) return colors.tier1;
  return colors.tier2;
};

const formatAmount = (amount: number) =>
  `£${amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;

export function TxnRow({ txn, onPress }: TxnRowProps) {
  const accent = tierColor(txn.tier);
  const isTier2 = txn.tier === 2;
  const isAutoPaid = txn.status === 'auto_paid';

  return (
    <Pressable
      style={({ pressed }) => [
        styles.row,
        isTier2 && { borderLeftColor: accent, borderLeftWidth: 2 },
        pressed && { opacity: 0.6 },
      ]}
      onPress={() => onPress?.(txn)}
    >
      <View style={styles.amountRow}>
        <Text style={styles.amount}>{formatAmount(txn.amount)}</Text>
        <View style={styles.tierBlock}>
          <Text style={[styles.tierLabel, { color: accent }]}>{tierLabel(txn.tier)}</Text>
          {isAutoPaid && <Text style={[styles.checkmark, { color: accent }]}>  ✓</Text>}
          {isTier2 && <Text style={[styles.upArrow, { color: accent }]}>  ▲</Text>}
        </View>
      </View>
      <Text style={styles.counterparty}>{txn.counterparty}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    paddingVertical: 18,
    paddingHorizontal: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#1A1208',
  },
  amountRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  amount: {
    ...type.amountList,
    color: colors.inkPrimary,
  },
  tierBlock: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  tierLabel: {
    ...type.caption,
  },
  checkmark: {
    ...type.caption,
  },
  upArrow: {
    ...type.caption,
    fontSize: 12,
  },
  counterparty: {
    ...type.body,
    color: colors.inkMono,
    marginTop: 4,
  },
});
