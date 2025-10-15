import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import clsx from "clsx";
import SignalTape from "@/components/SignalTape";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatAssetClass, formatSignalLine } from "@/lib/signal-formatters";
import { SignalRecord } from "@/types/signal";

interface SignalsResponse {
  data: SignalRecord[];
}

const fetchSignals = async (): Promise<SignalsResponse> => {
  const response = await fetch("/api/signals?limit=200");
  if (!response.ok) {
    throw new Error("Unable to load signals from API");
  }

  return response.json();
};

const parseTimestamp = (timestamp: string) => {
  if (!timestamp) return new Date();
  const normalized = timestamp.includes("T")
    ? timestamp
    : timestamp.replace(" ", "T");
  return new Date(`${normalized}Z`);
};

const OutputPanel = () => {
  const {
    data,
    isLoading,
    error,
    isFetching,
  } = useQuery<SignalsResponse>({
    queryKey: ["signals", { limit: 200 }],
    queryFn: fetchSignals,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    staleTime: 30_000,
  });

  const signals = data?.data ?? [];
  const tapeSignals = signals.slice(0, 40);

  const errorMessage =
    error instanceof Error ? error.message : error ? String(error) : undefined;

  return (
    <div className="flex h-full flex-col bg-editor-panel">
      <SignalTape
        signals={tapeSignals}
        isLoading={isLoading && !signals.length}
        error={errorMessage}
      />

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-3 p-4">
          {isLoading && !signals.length ? (
            <div className="rounded-xl border border-editor-border/60 bg-background/40 p-4 text-sm text-muted-foreground">
              Loading signal history…
            </div>
          ) : null}

          {!isLoading && !signals.length && !errorMessage ? (
            <div className="rounded-xl border border-dashed border-editor-border/60 bg-background/50 p-6 text-sm text-muted-foreground">
              Screens from the Investor cron job will appear here the moment a
              new signal fires.
            </div>
          ) : null}

          {signals.map((signal) => {
            const timestamp = parseTimestamp(signal.timestamp);
            const timestampLabel = Number.isNaN(timestamp.getTime())
              ? "Unknown time"
              : format(timestamp, "MMM d • HH:mm:ss");
            const line = formatSignalLine(signal);
            const assetClass = formatAssetClass(signal.asset_class);
            const changePositive = signal.change_pct >= 0;

            return (
              <div
                key={signal.id}
                className="rounded-2xl border border-editor-border bg-background/60 p-4 shadow-[0_10px_30px_rgba(0,0,0,0.25)] backdrop-blur"
              >
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-editor-border/70 px-2 py-0.5 text-[10px] uppercase tracking-[0.35em] text-muted-foreground/80">
                      {assetClass}
                    </span>
                    {signal.signal_type ? (
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-[0.25em]",
                          signal.signal_type === "L"
                            ? "border border-emerald-400/40 bg-emerald-500/10 text-emerald-300"
                            : "border border-red-400/40 bg-red-500/10 text-red-300"
                        )}
                      >
                        {signal.signal_type}
                      </span>
                    ) : null}
                  </div>
                  <span>{timestampLabel}</span>
                </div>

                <div
                  className={clsx(
                    "mt-3 font-mono text-sm",
                    changePositive ? "text-emerald-300" : "text-red-300"
                  )}
                >
                  {line}
                </div>
              </div>
            );
          })}

          {errorMessage && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">
              {errorMessage}
            </div>
          )}

          {isFetching && signals.length ? (
            <div className="pt-2 text-xs text-muted-foreground">
              Refreshing…
            </div>
          ) : null}
        </div>
      </ScrollArea>
    </div>
  );
};

export default OutputPanel;
