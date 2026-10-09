export type UserRole = 'directivo' | 'administradora' | 'cajera';

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface TreasuryAccount {
  id: number;
  name: string;
  currency: 'USD' | 'VES' | 'USDT';
  account_type: string;
  initial_balance: number;
  current_balance: number;
  is_active: boolean;
  only_income?: boolean;
}

export interface Transaction {
  id: number;
  branch_id?: number;
  date: string;
  movement_type: 'INGRESO' | 'EGRESO' | 'TRASPASO';
  subtype: string;
  amount_original: number;
  currency_original: string;
  exchange_rate: number;
  amount_usd: number;
  account_id?: number;
  destination_account_id?: number;
  category_id?: number;
  category_name?: string;
  doc_type?: string;
  doc_number?: string;
  beneficiary?: string;
  reference_number?: string;
  notes?: string;
  status: 'REGISTRADO' | 'ANULADO';
  created_at: string;
  created_by_name?: string;
}

export interface CreditRecord {
  id: number;
  sale_id: number;
  client_name: string;
  client_rif?: string;
  doc_type: string;
  doc_number: string;
  original_amount_usd: number;
  total_abonado_usd: number;
  pending_balance_usd: number;
  status: 'PENDIENTE' | 'PAGADO';
  is_cashea?: boolean;
  date: string;
}

export interface Category {
  id: number;
  name: string;
  code?: string;
  monthly_budget_usd?: number;
  spent_usd?: number;
}

export interface Supplier {
  id: number;
  name: string;
  rif?: string;
  phone?: string;
  bank_details?: string;
}

export interface CashCloseSummary {
  date: string;
  is_closed: boolean;
  bcv_rate: number;
  transactions_count: number;
  sales_summary: {
    fiscal_iva_usd: number;
    notes_credit_usd: number;
    notes_collected_usd: number;
    returns_total_usd: number;
    net_sales_usd: number;
  };
  collections_summary: {
    cash_usd: number;
    cash_ves: number;
    pos_total: number;
    pago_movil_usd: number;
    cashea_usd: number;
    retentions_iva_usd: number;
    retentions_islr_usd: number;
    expenses_caja_usd: number;
    total_collected_real_usd: number;
  };
  notes?: string;
  verified_by?: string;
}

export interface ArqueoUsdData {
  b100: number;
  b50: number;
  b20: number;
  b10: number;
  b5: number;
  b1: number;
}

export interface ArqueoVesData {
  b500: number;
  b200: number;
  b100: number;
  b50: number;
  b20: number;
  b10: number;
}
