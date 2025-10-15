import { useMemo } from "react";
import clsx from "clsx";
import { formatAssetClass, formatSignalLine } from "@/lib/signal-formatters";
import { SignalRecord } from "@/types/signal";

interface SignalTapeProps {
  signals: SignalRecord[];
  isLoading: boolean;
  error?: string;
}

const SignalTape = ({ signals, isLoading, error }: SignalTapeProps) => {
  const prepared = useMemo(() => {
    if (!signals.length) {
      return [];
    }
    return signals.map((signal) => ({
      id: signal.id,
      text: formatSignalLine(signal),
      isUp: signal.change_pct >= 0,
      assetClass: formatAssetClass(signal.asset_class),
    }));
  }, [signals]);

  const duplicated = useMemo(() => {
    if (prepared.length === 1) {
      // Need a minimum of two entries for a smooth marquee
      return [
        prepared[0],
        {
          ...prepared[0],
          id: `${prepared[0].id}-duplicate`,
        },
      ];
    }
    if (prepared.length === 0) {
      return [];
    }
    return [...prepared, ...prepared];
  }, [prepared]);

  const animationDuration = Math.max(prepared.length * 6, 28);

  if (error) {
    return (
      <div className="border-b border-editor-border bg-black/70 px-4 py-3 text-sm text-red-300">
        Signal tape unavailable — {error}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="border-b border-editor-border bg-black/70 px-4 py-3 text-sm text-muted-foreground">
        Loading latest screens…
      </div>
    );
  }

  if (!prepared.length) {
    return (
      <div className="border-b border-editor-border bg-black/70 px-4 py-3 text-sm text-muted-foreground">
        Waiting for the next screen from cron…
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden border-b border-editor-border bg-black text-green-200">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-black via-black/70 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-black via-black/70 to-transparent" />

      <div className="flex items-center gap-3 px-4 py-3">
        <span className="text-xs uppercase tracking-[0.35em] text-green-400">
          Signal Tape
        </span>
        <span className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_12px_rgba(74,222,128,0.8)] animate-pulse" />
      </div>

      <div className="overflow-hidden">
        <div
          className="signal-tape-track"
          style={{ animationDuration: `${animationDuration}s` }}
        >
          {duplicated.map((entry, index) => (
            <span
              key={`${entry.id}-${index}`}
              className={clsx(
                "inline-flex items-center gap-3 px-6 py-3 text-sm font-mono whitespace-nowrap",
                entry.isUp ? "text-emerald-300" : "text-red-300"
              )}
            >
              <span className="rounded-full border border-current/30 px-2 py-0.5 text-[10px] uppercase tracking-[0.4em] text-current/80">
                {entry.assetClass}
              </span>
              <span>{entry.text}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SignalTape;
