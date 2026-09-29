import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { research } from "@/lib/research";
import { int, num, pct } from "@/lib/utils";

export const Route = createFileRoute("/filters")({ component: Filters });

function Filters() {
  const f = research.filters;
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Stage 3</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Filter comparison</h1>
        <p className="mt-3 text-muted">
          Core parameters frozen at the least-bad IS set. Each filter is toggled alone. Retention was judged
          on <em>validation</em>, not OOS. {f.retention_rule}
        </p>
      </header>

      <Card>
        <CardHeader title="Chosen stack" kicker="Simplest thing that survived" />
        <p className="text-lg text-fg">
          <span className="font-mono">{f.chosen}</span>
          <span className="ml-3">
            <Badge>no additive filter</Badge>
          </span>
        </p>
        <p className="mt-2 text-sm text-muted">{f.chosen_note}</p>
        <p className="mt-3 text-sm text-muted">
          Mean-reversion folklore says “only trade when ADX is low / ER is choppy / session is London.” On
          this tape those rules change the <em>size</em> of the loss. They do not flip the sign of expectancy
          on validation.
        </p>
      </Card>

      <Card>
        <CardHeader title="Every filter, same parameters" kicker="VAL used to retain · OOS reported cold" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[56rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">Filter</th>
                <th className="pb-2 font-medium">Family</th>
                <th className="pb-2 font-medium">VAL n</th>
                <th className="pb-2 font-medium">VAL E</th>
                <th className="pb-2 font-medium">Δ VAL E</th>
                <th className="pb-2 font-medium">OOS n</th>
                <th className="pb-2 font-medium">OOS E</th>
                <th className="pb-2 font-medium">Δ OOS E</th>
                <th className="pb-2 font-medium">OOS WR</th>
                <th className="pb-2 font-medium">Keep?</th>
              </tr>
            </thead>
            <tbody>
              {f.table.map((row) => (
                <tr key={row.name} className="border-t border-border">
                  <td className="py-2">
                    <div className="font-mono text-xs text-fg">{row.name}</div>
                    <div className="max-w-[16rem] text-xs text-subtle">{row.note}</div>
                  </td>
                  <td className="py-2 text-muted">{row.family}</td>
                  <td className="py-2 font-mono tabular-nums">{int(row.val.trades)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.val.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.val_delta_e ?? 0, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{int(row.oos.trades)}</td>
                  <td className="py-2 font-mono tabular-nums text-negative">{num(row.oos.expectancy_r, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{num(row.oos_delta_e, 3)}</td>
                  <td className="py-2 font-mono tabular-nums">{pct(row.oos.win_rate)}</td>
                  <td className="py-2">{row.retained ? <Badge tone="good">yes</Badge> : <Badge>no</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader title="News filter" kicker="Mandatory module, historically untested" />
        <p className="text-sm leading-relaxed text-muted">
          High-impact EUR/USD event blackouts are implemented in the EA (MT5 economic calendar + CSV
          fallback). They were <strong className="font-medium text-fg">not</strong> validated on 2016–2026
          because no reliable dated event tape was available in this environment. Pretending otherwise would
          be a methodology failure. Enable the filter on demo if you want operational caution; do not credit
          it with historical edge.
        </p>
      </Card>
    </div>
  );
}
