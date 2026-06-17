import type { DecisionTrace } from "@/lib/types";
import { DecisionBadge } from "./Badges";
import { StageTimeline } from "./StageTimeline";

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </section>
  );
}

export function DecisionTraceViewer({ trace }: { trace: DecisionTrace }) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-violet-50 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-500">Claim ID</p>
            <p className="font-mono text-lg font-semibold text-slate-900">{trace.claim_id}</p>
          </div>
          <DecisionBadge decision={trace.decision} />
        </div>

        <dl className="mt-6 grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Approved amount</dt>
            <dd className="mt-1 text-2xl font-bold text-slate-900">
              {formatCurrency(trace.approved_amount)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Confidence</dt>
            <dd className="mt-1 text-2xl font-bold text-slate-900">
              {trace.confidence_score != null ? `${Math.round(trace.confidence_score * 100)}%` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Manual review</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900">
              {trace.manual_review_recommended ? "Recommended" : "Not required"}
            </dd>
          </div>
        </dl>
      </div>

      {trace.user_message && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950">
          <p className="text-sm font-semibold">Member message</p>
          <p className="mt-1 text-sm leading-relaxed">{trace.user_message}</p>
        </div>
      )}

      <Section title="Pipeline stages">
        <StageTimeline stages={trace.stages} />
      </Section>

      {trace.rejection_reasons.length > 0 && (
        <Section title="Rejection reasons">
          <ul className="flex flex-wrap gap-2">
            {trace.rejection_reasons.map((reason) => (
              <li
                key={reason}
                className="rounded-full bg-rose-100 px-3 py-1 text-sm font-medium text-rose-800"
              >
                {reason}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {trace.components_failed.length > 0 && (
        <Section title="Component failures">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {trace.components_failed.map((component) => (
              <li key={component}>{component}</li>
            ))}
          </ul>
        </Section>
      )}

      {trace.financial_breakdown && (
        <Section title="Financial breakdown">
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(trace.financial_breakdown, null, 2)}
          </pre>
        </Section>
      )}

      {trace.line_item_decisions && trace.line_item_decisions.length > 0 && (
        <Section title="Line item decisions">
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(trace.line_item_decisions, null, 2)}
          </pre>
        </Section>
      )}

      {trace.fraud_signals && trace.fraud_signals.length > 0 && (
        <Section title="Fraud signals">
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(trace.fraud_signals, null, 2)}
          </pre>
        </Section>
      )}
    </div>
  );
}
