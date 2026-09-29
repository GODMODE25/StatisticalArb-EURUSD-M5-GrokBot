import { createFileRoute, Link } from "@tanstack/react-router";
import { EquityChart, YearlyChart } from "@/components/charts";
import { ExitMix, Metric, MetricsGrid, eTone } from "@/components/metrics";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { research } from "@/lib/research";
import { int, num, pct, rUnit } from "@/lib/utils";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({ component: Home });

const GATE_LABEL: Record<string, string> = {
  oos_net_expectancy_positive: "OOS net expectancy > 0",
  oos_pf_ge_1_15: "OOS profit factor ≥ 1.15",
  full_trades_ge_1000: "Full sample ≥ 1,000 trades",
  oos_trades_ge_150: "OOS sample large enough",
  walk_forward_aggregate_positive: "Walk-forward aggregate > 0",
  base_cost_oos_positive: "Base-cost OOS > 0",
  adverse_cost_oos_positive: "Adverse-cost OOS > 0",
  win_rate_near_45: "OOS win rate near 45%",
};

function Home() {
  const m = research.meta;
  const c = research.candidate;
  const costDrag = research.costs.gross_full.expectancy_r - c.full.expectancy_r;
  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Statistical review</p>
        <h1 className="mt-2 font-display text-[2.1rem] leading-[1.15] tracking-tight text-fg sm:text-5xl">
          The hypothesis does not survive costs.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-muted sm:text-lg">
          {m.verdict_text}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Badge tone="bad">{m.verdict.replaceAll("_", " ")}</Badge>
          <Badge>EURUSD M5</Badge>
          <Badge>{int(research.data.m5_bars)} M5 bars</Badge>
          <Badge>2016–2026</Badge>
        </div>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <Metric label="IS expectancy" value={rUnit(c.is.expectancy_r)} tone={eTone(c.is.expectancy_r)} hint={`${int(c.is.trades)} trades · 2016–21`} />
        </Card>
        <Card>
          <Metric label="OOS expectancy" value={rUnit(c.oos.expectancy_r)} tone={eTone(c.oos.expectancy_r)} hint={`${int(c.oos.trades)} trades · 2024–25`} />
        </Card>
        <Card>
          <Metric label="Walk-forward E" value={rUnit(research.walk_forward.aggregate.expectancy_r)} tone="bad" hint={`${int(research.walk_forward.aggregate.trades)} test trades`} />
        </Card>
        <Card>
          <Metric label="Cost drag vs gross" value={rUnit(-costDrag)} tone="bad" hint={`${num(research.costs.base_round_turn_pips, 1)} pip round-turn / 15 pip SL`} />
        </Card>
      </div>

      <Card>
        <CardHeader kicker="Pre-declared gates" title="Nothing that had to be true was true — except sample size." />
        <ul className="grid gap-2 sm:grid-cols-2">
          {Object.entries(m.gates).map(([k, v]) => (
            <li key={k} className="flex items-start gap-3 rounded-lg bg-elevated px-3 py-2.5">
              <span className={v ? "text-positive" : "text-negative"}>{v ? "Pass" : "Fail"}</span>
              <span className="text-sm text-fg">{GATE_LABEL[k] ?? k}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardHeader kicker="What the study actually found" title="Eight facts, none of them a trading edge." />
        <ol className="space-y-3">
          {m.key_findings.map((f, i) => (
            <li key={i} className="flex gap-3 text-sm leading-relaxed text-muted sm:text-base">
              <span className="mt-0.5 font-mono text-xs text-subtle">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-fg">{f}</span>
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        <CardHeader
          kicker="Least-bad configuration · 1% compounded equity"
          title="Starting $10,000 is effectively gone."
        />
        <p className="mb-4 text-sm text-muted">
          Compounding 1% of equity on a negative-expectancy stream. This is not a “max DD of a good system” —
          it is ruin. Nominal 1:2 never showed up: TP share {pct(c.full.tp_share)}, time-stop share {pct(c.full.time_stop_share)},
          average winner {rUnit(c.full.avg_win_r, 2)}.
        </p>
        <EquityChart />
        <p className="mt-3 font-mono text-xs text-subtle">
          Terminal multiple {num(c.full.end_equity_multiple, 4)} · max DD {num(c.full.max_dd_pct_1pct_risk, 1)}%
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader kicker="Every calendar year" title="No hidden winning regime." />
          <YearlyChart />
        </Card>
        <Card>
          <CardHeader kicker="How trades actually died" title="The 2R target is rare." />
          <ExitMix m={c.full} />
          <p className="mt-4 text-sm text-muted">
            A 15-pip stop and 30-pip target on a market whose M5 ATR is about 3.8 pips is a trend-sized target
            hanging on a mean-reversion idea. Time stops close nearly half the book at ~1R, not 2R.
          </p>
        </Card>
      </div>

      <Card>
        <CardHeader kicker="Full sample after base costs" title="Least-bad researched defaults" />
        <MetricsGrid m={c.full} />
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/ea" className={cn(buttonVariants())}>
            Download the EA
          </Link>
          <Link to="/plan" className={cn(buttonVariants({ variant: "secondary" }))}>
            Read the protocol
          </Link>
        </div>
      </Card>
    </div>
  );
}
