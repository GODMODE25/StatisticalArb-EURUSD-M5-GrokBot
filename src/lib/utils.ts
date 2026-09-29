import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function pct(x: number, digits = 1) {
  if (!Number.isFinite(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function num(x: number, digits = 2) {
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(digits);
}

export function signed(x: number, digits = 3) {
  if (!Number.isFinite(x)) return "—";
  const v = x.toFixed(digits);
  return x > 0 ? `+${v}` : v;
}

export function rUnit(x: number, digits = 3) {
  return `${signed(x, digits)}R`;
}

export function int(x: number) {
  if (!Number.isFinite(x)) return "—";
  return Math.round(x).toLocaleString();
}
