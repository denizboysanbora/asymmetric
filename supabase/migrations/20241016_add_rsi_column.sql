-- Add RSI column to signals table
ALTER TABLE signals ADD COLUMN rsi DECIMAL DEFAULT 50.0;

-- Update existing records to have default RSI value
UPDATE signals SET rsi = 50.0 WHERE rsi IS NULL;
