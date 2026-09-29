import { createFileRoute } from "@tanstack/react-router";
import { EquityChart, Heatmap, YearlyChart } from "@/components/charts";
import { ExitMix, MetricsGrid } from "@/components/metrics";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { confirmLabel, priceLabel, research, slLabel, splits } from "@/lib/research";
import { int, num, pct } from "@/lib/utils";

export const Route = createFileRoute("/candidate")({ component: Candidate });

function Candidate() {
  const c = research.candidate;
  const cfg = c.cfg;
  const mc = research.monte_carlo;
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Stages 4–5</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Least-bad candidate</h1>
        <p className="mt-3 text-muted">
          Not a validated system. This is the configuration that lost the least in-sample after costs,
          with validation and OOS reported honestly.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="bad">Not validated</Badge>
          <Badge>Filter: {c.filter}</Badge>
          <Badge>Win-rate ≥45% OOS: {c.win_rate_target_45_met ? "yes" : "no"}</Badge>
        </div>
      </header>

      <Card>
        <CardHeader title="Exact parameter set" kicker={c.id} />
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
          {[
            ["Price", priceLabel(cfg.price)],
            ["Lookback", String(cfg.lookback)],
            ["Z entry", String(cfg.z_entry)],
            ["Confirm", confirmLabel(cfg.confirm)],
            ["SL", slLabel(cfg)],
            ["TP", `${cfg.tp_rr} × SL`],
            ["Max hold", `${cfg.max_hold} bars`],
            ["Cooldown", `${cfg.cooldown} bars`],
            ["Z-exit", cfg.z_exit === 0 ? "off" : String(cfg.z_exit)],
            ["Risk", "1% current equity"],
            ["Magic", String(research.ea.magic)],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-elevated px-3 py-2">
              <dt className="text-xs text-subtle">{k}</dt>
              <dd className="mt-0.5 font-mono text-fg">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {splits.map((s) => {
          const m = s.key === "extra_2026" ? c.extra_2026 : c[s.key];
          return (
            <Card key={s.key}>
              <CardHeader kicker={s.hint} title={`${s.label} · ${s.range}`} />
              <MetricsGrid m={m} compact />
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader title="Compounded 1% equity" kicker="Full tape, base costs" />
        <EquityChart />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Year by year" kicker="No rescue year" />
          <YearlyChart />
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-subtle">
                <tr>
                  <th className="pb-2 font-medium">Year</th>
                  <th className="pb-2 font-medium">n</th>
                  <th className="pb-2 font-medium">WR</th>
                  <th className="pb-2 font-medium">E</th>
                  <th className="pb-2 font-medium">PF</th>
                </tr>
              </thead>
              <tbody>
                {c.yearly.map((y) => (
                  <tr key={y.year} className="border-t border-border">
                    <td className="py-1.5 font-mono">{y.year}</td>
                    <td className="py-1.5 font-mono tabular-nums">{int(y.trades)}</td>
                    <td className="py-1.5 font-mono tabular-nums">{pct(y.win_rate)}</td>
                    <td className="py-1.5 font-mono tabular-nums text-negative">{num(y.expectancy_r, 3)}</td>
                    <td className="py-1.5 font-mono tabular-nums">{num(y.profit_factor, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card>
          <CardHeader title="Exit mix · full sample" />
          <ExitMix m={c.full} />
        </Card>
      </div>

      <Card>
        <CardHeader title="Lookback × Z heatmap" kicker="OOS expectancy (all negative)" />
        <Heatmap />
      </Card>

      <Card>
        <CardHeader title="Stop distance" kicker="Monotone in the wrong direction" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">SL</th>
                <th className="pb-2 font-medium">IS n</th>
                <th className="pb-2 font-medium">IS E</th>
                <th className="pb-2 font-medium">OOS n</th>
                <th className="pb-2 font-medium">OOS E</th>
                <th className="pb-2 font-medium">OOS PF</th>
              </tr>
            </thead>
            <tbody>
              {research.stability.stops.map((s) => (
                <tr key={s.label} className="border-t border-border">
                  <td className="py-2">{s.label}</td>
                  <td className="py-2 font-mono tabular-nums">{int(s.is.trades)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(s.is.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{int(s.oos.trades)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(s.oos.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(s.oos.profit_factor, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Walk-forward"
          kicker="12-month train / 3-month test, step 3 months"
        />
        <p className="mb-3 text-sm text-muted">{research.walk_forward.design}</p>
        <MetricsGrid m={research.walk_forward.aggregate} compact />
        <p className="mt-4 text-sm text-muted">
          {"Train windows with E>0:"} 0 / {research.walk_forward.windows.length}. {"Test windows with E>0:"}{" "}
          {research.walk_forward.windows.filter((w) => w.test.expectancy_r > 0).length} /{" "}
          {research.walk_forward.windows.length} (noise, not a system). Lookbacks used:{" "}
          {research.walk_forward.param_drift.lookback_unique.join(", ")}. Z mode{" "}
          {research.walk_forward.param_drift.z_mode}.
        </p>
      </Card>

      <Card>
        <CardHeader title="Monte Carlo" kicker={mc.note} />
        <div className="grid gap-4 md:grid-cols-2">
          <McBlock title="OOS IID bootstrap (1,000 paths)" data={mc.oos_iid} />
          <McBlock title="Full-sample IID" data={mc.full_iid} />
          <McBlock title="OOS haircut winners −15% / fatten losses +15%" data={mc.oos_haircut_winners_15_fatten_losses_15} />
          <McBlock title="OOS block bootstrap (block=8)" data={mc.oos_block_bootstrap} />
        </div>
        <p className="mt-4 text-sm text-muted">
          At 1% risk, the probability of a 20% drawdown on the OOS trade list is 100%, and the probability
          of halving the account is 99.8%. Monte Carlo is not a way to rescue a negative stream.
        </p>
      </Card>

      <Card>
        <CardHeader title="Limitations" />
        <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
          {research.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function McBlock({ title, data }: { title: string; data: Record<string, number | string> }) {
  if (!data || data.paths === 0) {
    return (
      <div className="rounded-lg bg-elevated p-3 text-sm text-muted">
        {title}: insufficient trades
      </div>
    );
  }
  const rows: [string, unknown][] = [
    ["Median end equity", data.median_end_equity],
    ["5th pct end equity", data.p05_end_equity],
    ["Median max DD", data.median_max_dd_pct != null ? `${data.median_max_dd_pct}%` : data.median_max_dd_pct],
    ["95th pct max DD", data.p95_max_dd_pct != null ? `${data.p95_max_dd_pct}%` : data.p95_max_dd_pct],
    ["P(DD ≥ 20%)", data.prob_dd_ge_20pct],
    ["P(equity < 50%)", data.prob_equity_below_50pct],
  ];
  return (
    <div className="rounded-lg bg-elevated p-3">
      <h3 className="text-sm font-medium text-fg">{title}</h3>
      <dl className="mt-2 space-y-1 text-sm">
        {rows
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="text-muted">{k}</dt>
              <dd className="font-mono tabular-nums text-fg">{String(v)}</dd>
            </div>
          ))}
      </dl>
    </div>
  );
}
