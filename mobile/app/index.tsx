import { router } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BloomGradient } from '@/components/BloomGradient';
import { PulseDot } from '@/components/PulseDot';
import { TxnRow } from '@/components/TxnRow';
import { pendingTransactions, settledTransactions } from '@/data/mockTransactions';
import { colors } from '@/tokens/colors';
import { type } from '@/tokens/typography';
import { Transaction } from '@/types/transaction';

export default function TransactionList() {
  const insets = useSafeAreaInsets();

  const handleTxnPress = (txn: Transaction) => {
    if (txn.status === 'auto_paid') return;
    if (txn.tier === 3) {
      router.push({ pathname: '/vouch', params: { id: txn.id } });
    } else if (txn.tier === 2) {
      router.push({ pathname: '/approve', params: { id: txn.id } });
    }
  };

  return (
    <BloomGradient>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingTop: insets.top + 18, paddingBottom: insets.bottom + 40 }}
      >
        <View style={styles.headerRow}>
          <View style={styles.brandBlock}>
            <PulseDot size={7} />
            <Text style={styles.brand}>VOUCH</Text>
          </View>
          <Text style={styles.gear}>⚙</Text>
        </View>

        <View style={styles.sectionHead}>
          <Text style={styles.sectionLabel}>
            TODAY · {pendingTransactions.filter(t => t.status === 'pending').length} PENDING
          </Text>
          <Text style={styles.sectionTotal}>
            £{pendingTransactions.reduce((s, t) => s + t.amount, 0).toLocaleString('en-GB')}
          </Text>
        </View>

        {pendingTransactions.map((txn) => (
          <TxnRow key={txn.id} txn={txn} onPress={handleTxnPress} />
        ))}

        <View style={{ height: 28 }} />

        <View style={styles.sectionHead}>
          <Text style={styles.sectionLabel}>YESTERDAY · {settledTransactions.length} SETTLED</Text>
          <Text style={styles.sectionTotal}>
            £{settledTransactions.reduce((s, t) => s + t.amount, 0).toLocaleString('en-GB')}
          </Text>
        </View>

        {settledTransactions.map((txn) => (
          <TxnRow key={txn.id} txn={txn} onPress={handleTxnPress} />
        ))}

        <View style={{ height: 60 }} />
        <Text style={styles.footerNote}>Vouch · Plaid sandbox · Specter live</Text>
      </ScrollView>
    </BloomGradient>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginBottom: 28,
  },
  brandBlock: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  brand: {
    ...type.caption,
    color: colors.inkPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  gear: {
    color: colors.inkMono,
    fontSize: 18,
  },
  sectionHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingHorizontal: 22,
    marginBottom: 14,
  },
  sectionLabel: {
    ...type.caption,
    color: colors.inkMono,
  },
  sectionTotal: {
    ...type.caption,
    color: colors.inkMuted,
    fontSize: 10,
  },
  footerNote: {
    ...type.caption,
    color: colors.inkMuted,
    textAlign: 'center',
    marginTop: 30,
  },
});
