import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/card";
import { confirmLabel, priceLabel, research, slLabel } from "@/lib/research";
import { int, num, pct } from "@/lib/utils";

export const Route = createFileRoute("/baseline")({ component: Baseline });

function Baseline() {
  const b = research.baseline;
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Stages 1–2</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Baseline grid</h1>
        <p className="mt-3 text-muted">{b.note}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs uppercase tracking-wider text-subtle">Configs tested</p>
          <p className="mt-1 font-mono text-2xl tabular-nums">{int(b.grid_size)}</p>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wider text-subtle">IS sample ≥ 300 trades</p>
          <p className="mt-1 font-mono text-2xl tabular-nums">{int(b.is_sampled)}</p>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wider text-subtle">{"IS E>0 and PF>1"}</p>
          <p className="mt-1 font-mono text-2xl tabular-nums text-negative">{int(b.is_profitable)}</p>
        </Card>
      </div>

      <Card>
        <CardHeader title="Least-bad 15 by in-sample expectancy" kicker="All negative after costs" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">#</th>
                <th className="pb-2 font-medium">Lookback</th>
                <th className="pb-2 font-medium">Z</th>
                <th className="pb-2 font-medium">Confirm</th>
                <th className="pb-2 font-medium">SL</th>
                <th className="pb-2 font-medium">Hold</th>
                <th className="pb-2 font-medium">IS n</th>
                <th className="pb-2 font-medium">IS E</th>
                <th className="pb-2 font-medium">IS WR</th>
                <th className="pb-2 font-medium">IS PF</th>
                <th className="pb-2 font-medium">OOS E</th>
              </tr>
            </thead>
            <tbody>
              {b.leaderboard.map((row, i) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="py-2 font-mono text-subtle">{i + 1}</td>
                  <td className="py-2 font-mono">{row.cfg.lookback}</td>
                  <td className="py-2 font-mono">{row.cfg.z_entry}</td>
                  <td className="py-2">{confirmLabel(row.cfg.confirm)}</td>
                  <td className="py-2 font-mono">{slLabel(row.cfg)}</td>
                  <td className="py-2 font-mono">{row.cfg.max_hold}</td>
                  <td className="py-2 font-mono tabular-nums">{int(row.is.trades)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.is.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{pct(row.is.win_rate)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.is.profit_factor, 2)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.oos.expectancy_r, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader title="Price / confirm / hold variants around the core" kicker="Still selected on IS, reported on OOS" />
        <p className="mb-4 text-sm text-muted">
          Typical price, residual, close, ATR-normalized deviation; immediate / reversal / persist / re-entry;
          holds 12–96; optional z-exit at 0.25. None produced positive IS expectancy. Residual is essentially
          tied with typical and does not change the conclusion.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">Price</th>
                <th className="pb-2 font-medium">Confirm</th>
                <th className="pb-2 font-medium">Hold</th>
                <th className="pb-2 font-medium">Z-exit</th>
                <th className="pb-2 font-medium">IS E</th>
                <th className="pb-2 font-medium">VAL E</th>
                <th className="pb-2 font-medium">OOS E</th>
                <th className="pb-2 font-medium">IS WR</th>
              </tr>
            </thead>
            <tbody>
              {research.variants.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="py-2">{priceLabel(row.cfg.price)}</td>
                  <td className="py-2">{confirmLabel(row.cfg.confirm)}</td>
                  <td className="py-2 font-mono">{row.cfg.max_hold}</td>
                  <td className="py-2 font-mono">{row.cfg.z_exit}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.is.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.val.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.oos.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{pct(row.is.win_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
