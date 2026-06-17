import type { StageTrace } from "@/lib/types";
import { DOT_STYLES, StatusBadge } from "./Badges";

function StageDetails({ stage }: { stage: StageTrace }) {
  const hasChecks = stage.checks.length > 0;
  const hasMessages = stage.messages.length > 0;
  const hasFields = stage.fields && Object.keys(stage.fields).length > 0;

  if (!hasChecks && !hasMessages && !hasFields && !stage.rule && !stage.detail) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 text-sm text-slate-600">
      {stage.rule && (
        <p>
          <span className="font-medium text-slate-800">Rule:</span> {stage.rule}
        </p>
      )}
      {stage.detail && <p>{stage.detail}</p>}
      {hasMessages && (
        <ul className="list-disc space-y-1 pl-5">
          {stage.messages.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      {hasChecks && (
        <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
          {JSON.stringify(stage.checks, null, 2)}
        </pre>
      )}
      {hasFields && (
        <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
          {JSON.stringify(stage.fields, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function StageTimeline({ stages }: { stages: StageTrace[] }) {
  return (
    <ol className="relative space-y-0">
      {stages.map((stage, index) => (
        <li key={`${stage.stage}-${index}`} className="relative flex gap-4 pb-8 last:pb-0">
          {index < stages.length - 1 && (
            <span
              aria-hidden
              className="absolute left-[11px] top-6 h-[calc(100%-12px)] w-px bg-slate-200"
            />
          )}
          <span
            aria-hidden
            className={`relative z-10 mt-1.5 h-6 w-6 shrink-0 rounded-full ring-4 ring-white ${DOT_STYLES[stage.status]}`}
          />
          <div className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-900">{stage.stage.replace(/_/g, " ")}</h3>
              <StatusBadge status={stage.status} />
            </div>
            <StageDetails stage={stage} />
          </div>
        </li>
      ))}
    </ol>
  );
}
