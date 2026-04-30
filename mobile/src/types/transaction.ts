export type Tier = 1 | 2 | 3;

export type TxnStatus = 'pending' | 'auto_paid' | 'approved' | 'rejected' | 'blocked';

export type SpecterGrade = 'A+' | 'A' | 'B' | 'C' | 'D' | 'unknown';

export interface Transaction {
  id: string;
  amount: number;
  currency: 'GBP';
  counterparty: string;
  category: string;
  tier: Tier;
  status: TxnStatus;
  createdAt: string;
  specterGrade: SpecterGrade;
  specterNote?: string;
  priorPayments: number;
  lastPaidAt?: string;
  explainer?: string;
  approversRequired?: number;
  approversCompleted?: number;
  domain?: string;
  logoUrl?: string;
  reference?: string;
  account?: string;
  method?: string;
  dateLabel?: string;
  brandColor?: string;
  recurring?: boolean;
  timeToClear?: string;
  remoteVouchOutcome?: 'approved' | 'rejected';
  remoteVouchReason?: string;
}

export interface BiometricResult {
  faceIdPassed: boolean;
  emotion: 'neutral' | 'stressed' | 'fearful' | 'coerced';
  cadence: 'ok' | 'rushed' | 'forced';
  vouchedAt: string;
}
