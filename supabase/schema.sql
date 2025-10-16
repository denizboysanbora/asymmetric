-- Complete signals table schema
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    price DECIMAL NOT NULL,
    change_pct DECIMAL NOT NULL,
    rsi DECIMAL NOT NULL DEFAULT 50.0,
    tr_atr DECIMAL NOT NULL,
    z_score DECIMAL NOT NULL,
    signal_type TEXT NOT NULL,
    asset_class TEXT NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_asset_class ON signals(asset_class);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON signals(signal_type);
