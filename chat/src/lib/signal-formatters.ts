import { SignalRecord } from "@/types/signal";

const formatPrice = (price: number) => {
  if (price >= 1000) {
    return `$${Math.round(price).toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })}`;
  }

  return `$${price.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const formatWithSign = (value: number, fractionDigits = 2) => {
  return `${value >= 0 ? "+" : ""}${value.toFixed(fractionDigits)}`;
};

export const formatSignalLine = (signal: SignalRecord) => {
  const price = formatPrice(signal.price);
  const pct = formatWithSign(signal.change_pct);
  const trAtr = signal.tr_atr.toFixed(2);
  const zScore = signal.z_score.toFixed(2);
  const code = signal.signal_type?.trim();

  let line = `$${signal.symbol} ${price} ${pct}% | ${trAtr}x ATR | Z ${zScore}`;
  if (code) {
    line += ` | ${code}`;
  }

  return line;
};

export const formatAssetClass = (assetClass: string) => {
  if (!assetClass) return "SIGNAL";
  return assetClass.toUpperCase();
};
