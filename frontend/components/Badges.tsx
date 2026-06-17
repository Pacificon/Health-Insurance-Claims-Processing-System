import type { StageStatus } from "@/lib/types";

const STATUS_STYLES: Record<StageStatus, string> = {
  PASSED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  FAILED: "border-rose-200 bg-rose-50 text-rose-800",
  SKIPPED: "border-slate-200 bg-slate-50 text-slate-500",
  WARNING: "border-amber-200 bg-amber-50 text-amber-800",
};

const DOT_STYLES: Record<StageStatus, string> = {
  PASSED: "bg-emerald-500",
  FAILED: "bg-rose-500",
  SKIPPED: "bg-slate-300",
  WARNING: "bg-amber-500",
};

export function StatusBadge({ status }: { status: StageStatus }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export function DecisionBadge({ decision }: { decision: string | null }) {
  if (!decision) {
    return (
      <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-800">
        Action required
      </span>
    );
  }

  const styles: Record<string, string> = {
    APPROVED: "border-emerald-200 bg-emerald-50 text-emerald-800",
    PARTIAL: "border-sky-200 bg-sky-50 text-sky-800",
    REJECTED: "border-rose-200 bg-rose-50 text-rose-800",
    MANUAL_REVIEW: "border-violet-200 bg-violet-50 text-violet-800",
  };

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${styles[decision] ?? "border-slate-200 bg-slate-50 text-slate-700"}`}
    >
      {decision.replace("_", " ")}
    </span>
  );
}

export { DOT_STYLES, STATUS_STYLES };
