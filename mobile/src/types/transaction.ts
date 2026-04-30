export type Tier = 0 | 1 | 2;

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
}

export interface BiometricResult {
  faceIdPassed: boolean;
  emotion: 'neutral' | 'stressed' | 'fearful' | 'coerced';
  cadence: 'ok' | 'rushed' | 'forced';
  vouchedAt: string;
}
