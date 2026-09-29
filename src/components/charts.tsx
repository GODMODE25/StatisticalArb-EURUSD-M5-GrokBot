import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { research } from "@/lib/research";
import { num } from "@/lib/utils";

const tooltipStyle = {
  background: "#141518",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8,
  fontSize: 12,
  color: "#ecece8",
};

export function EquityChart() {
  const data = research.candidate.equity_curve;
  return (
    <div className="h-64 w-full sm:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#b45a4e" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#b45a4e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="t" tick={{ fill: "#9a9aa3", fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={48} />
          <YAxis
            tick={{ fill: "#9a9aa3", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${Math.round(v / 1000)}k`}
            width={40}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v: number | string) => [`${Number(v).toFixed(0)}`, "Equity"]}
            labelFormatter={(l: string) => String(l)}
          />
          <Area type="monotone" dataKey="equity" stroke="#b45a4e" strokeWidth={1.6} fill="url(#eq)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function YearlyChart() {
  const data = research.candidate.yearly.map((y) => ({
    year: String(y.year),
    e: Number(y.expectancy_r.toFixed(3)),
  }));
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "#9a9aa3", fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: "#9a9aa3", fontSize: 11 }} tickLine={false} axisLine={false} width={44} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number | string) => [`${v}R`, "Expectancy"]} />
          <Bar dataKey="e" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.year} fill={d.e >= 0 ? "#6b8f71" : "#b45a4e"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Heatmap() {
  const cells = research.stability.lookback_z;
  const zs = [...new Set(cells.map((c) => c.z_entry))].sort((a, b) => a - b);
  const lbs = [...new Set(cells.map((c) => c.lookback))].sort((a, b) => a - b);
  const min = Math.min(...cells.map((c) => c.oos_e));
  const max = Math.max(...cells.map((c) => c.oos_e));
  function color(e: number) {
    const t = (e - min) / Math.max(1e-9, max - min);
    const r = Math.round(180 - t * 40);
    const g = Math.round(50 + t * 40);
    const b = Math.round(50 + t * 20);
    return `rgb(${r},${g},${b})`;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[28rem] border-separate border-spacing-1 text-center">
        <thead>
          <tr>
            <th className="text-left text-xs font-medium text-subtle">Lookback \\ Z</th>
            {zs.map((z) => (
              <th key={z} className="text-xs font-medium text-muted">
                {z}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lbs.map((lb) => (
            <tr key={lb}>
              <td className="pr-2 text-left font-mono text-xs tabular-nums text-muted">{lb}</td>
              {zs.map((z) => {
                const cell = cells.find((c) => c.lookback === lb && c.z_entry === z);
                if (!cell) return <td key={z} />;
                return (
                  <td key={z}>
                    <div
                      className="rounded-md px-1 py-2 font-mono text-[11px] tabular-nums text-fg"
                      style={{ background: color(cell.oos_e) }}
                      title={`IS ${cell.is_e.toFixed(3)}R n=${cell.is_n} · OOS ${cell.oos_e.toFixed(3)}R n=${cell.oos_n}`}
                    >
                      {num(cell.oos_e, 3)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted">
        Cell color is OOS expectancy (all cells are negative). Darker red is worse. Hover for IS vs OOS.
      </p>
    </div>
  );
}
