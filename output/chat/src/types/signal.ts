export interface SignalRecord {
  id: number;
  timestamp: string;
  symbol: string;
  price: number;
  change_pct: number;
  tr_atr: number;
  z_score: number;
  signal_type: string;
  asset_class: string;
}

