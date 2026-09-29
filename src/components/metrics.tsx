import type { Metrics } from "@/lib/research";
import { cn, int, num, pct, rUnit } from "@/lib/utils";

export function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "good" | "bad" | "neutral";
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-subtle">{label}</p>
      <p
        className={cn(
          "mt-1 font-mono text-lg tabular-nums sm:text-xl",
          tone === "good" && "text-positive",
          tone === "bad" && "text-negative",
          (!tone || tone === "neutral") && "text-fg",
        )}
      >
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

export function eTone(x: number): "good" | "bad" | "neutral" {
  if (x > 0.005) return "good";
  if (x < -0.005) return "bad";
  return "neutral";
}

export function MetricsGrid({ m, compact }: { m: Metrics; compact?: boolean }) {
  const items = [
    { label: "Trades", value: int(m.trades) },
    { label: "Win rate", value: pct(m.win_rate), tone: m.win_rate >= 0.45 ? ("good" as const) : ("bad" as const) },
    { label: "Expectancy", value: rUnit(m.expectancy_r), tone: eTone(m.expectancy_r) },
    { label: "Profit factor", value: num(m.profit_factor, 2), tone: eTone(m.profit_factor - 1) },
    { label: "Avg win", value: rUnit(m.avg_win_r, 2) },
    { label: "Avg loss", value: rUnit(m.avg_loss_r, 2) },
    { label: "Payoff", value: num(m.payoff, 2) },
    { label: "Max DD (1% risk)", value: `${num(m.max_dd_pct_1pct_risk, 1)}%`, tone: "bad" as const },
  ];
  const shown = compact ? items.slice(0, 4) : items;
  return (
    <div className={cn("grid gap-4", compact ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-4")}>
      {shown.map((it) => (
        <Metric key={it.label} {...it} />
      ))}
    </div>
  );
}

export function ExitMix({ m }: { m: Metrics }) {
  const rows = [
    { k: "Stop-loss", v: m.sl_share },
    { k: "Take-profit", v: m.tp_share },
    { k: "Time stop", v: m.time_stop_share },
    { k: "Z-exit", v: m.z_exit_share },
  ];
  return (
    <ul className="space-y-2">
      {rows.map((r) => (
        <li key={r.k}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-muted">{r.k}</span>
            <span className="font-mono tabular-nums text-fg">{pct(r.v)}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-elevated">
            <div className="h-full rounded-full bg-accent/80" style={{ width: `${Math.max(0, Math.min(100, r.v * 100))}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
