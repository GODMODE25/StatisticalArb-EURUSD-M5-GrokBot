import { createFileRoute } from "@tanstack/react-router";
import { MetricsGrid } from "@/components/metrics";
import { Card, CardHeader } from "@/components/ui/card";
import { research } from "@/lib/research";
import { int, num } from "@/lib/utils";

export const Route = createFileRoute("/data")({ component: DataPage });

function DataPage() {
  const d = research.data;
  const years = Object.entries(d.bars_by_year);
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Stage 0 · tape</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Data and costs</h1>
        <p className="mt-3 text-muted">
          All reported numbers include the base cost model unless labeled “gross / zero-cost,” and those
          zero-cost figures were never used for selection.
        </p>
      </header>

      <Card>
        <CardHeader title="EURUSD M5 tape" kicker={d.source} />
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wider text-subtle">M1 prints</dt>
            <dd className="mt-1 font-mono text-lg tabular-nums">{int(d.m1_bars)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-subtle">M5 bars</dt>
            <dd className="mt-1 font-mono text-lg tabular-nums">{int(d.m5_bars)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-subtle">Start</dt>
            <dd className="mt-1 font-mono text-sm">{d.start}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-subtle">End</dt>
            <dd className="mt-1 font-mono text-sm">{d.end}</dd>
          </div>
        </dl>
        <p className="mt-4 text-sm text-muted">{d.timestamp_convention}</p>
        <p className="mt-2 text-sm text-muted">{d.gaps_note}</p>
        <p className="mt-2 text-sm text-muted">{d.tick_model}</p>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[20rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">Year</th>
                <th className="pb-2 font-medium">M5 bars</th>
              </tr>
            </thead>
            <tbody>
              {years.map(([y, n]) => (
                <tr key={y} className="border-t border-border">
                  <td className="py-1.5 font-mono">{y}</td>
                  <td className="py-1.5 font-mono tabular-nums">{int(Number(n))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader title="Cost model" kicker={research.costs.model} />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">Scenario</th>
                <th className="pb-2 font-medium">Spread</th>
                <th className="pb-2 font-medium">Slip (1-way)</th>
                <th className="pb-2 font-medium">Comm RT</th>
                <th className="pb-2 font-medium">RT pips</th>
                <th className="pb-2 font-medium">OOS E</th>
                <th className="pb-2 font-medium">Full E</th>
              </tr>
            </thead>
            <tbody>
              {research.costs.table.map((row) => (
                <tr key={row.scenario} className="border-t border-border">
                  <td className="py-2">
                    <div className="text-fg">{row.label}</div>
                    <div className="font-mono text-xs text-subtle">{row.scenario}</div>
                  </td>
                  <td className="py-2 font-mono tabular-nums">{num(row.spread_pips, 1)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.slippage_pips_one_way, 2)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.commission_pips_rt, 2)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.round_turn_pips, 2)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.oos.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.full.expectancy_r, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-sm text-muted">
          On a 15-pip stop, base round-turn 2.5 pips is 0.17R per trade. That single line is larger than the
          entire zero-cost full-sample expectancy ({num(research.costs.gross_full.expectancy_r, 3)}R).
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Gross (zero-cost) — diagnostic only" kicker="Not used for selection" />
          <p className="mb-4 text-sm text-muted">{research.costs.gross_vs_net_note}</p>
          <h3 className="mb-3 text-sm text-muted">Full sample</h3>
          <MetricsGrid m={research.costs.gross_full} compact />
          <h3 className="mb-3 mt-6 text-sm text-muted">OOS 2024–2025</h3>
          <MetricsGrid m={research.costs.gross_oos} compact />
        </Card>
        <Card>
          <CardHeader title="Why tiny stops are dead on arrival" kicker="Spread-to-stop" />
          <p className="text-sm leading-relaxed text-muted">
            M5 ATR on this tape is about 3.8 pips. An 8-pip stop pays 2.5 / 8 = 0.31R in friction before the
            idea has a chance. The stop table on the candidate page is monotone: larger stops lose less,
            smaller stops lose more. None of them make money after costs.
          </p>
          <p className="mt-4 text-sm text-muted">
            Variable broker spread is not in HistData. If live spread is worse than 1.2 pips, the base case
            is optimistic. The adverse case (4.2 pips RT) is the stress view, not a caricature of a news
            spike — that would be worse still.
          </p>
        </Card>
      </div>
    </div>
  );
}
