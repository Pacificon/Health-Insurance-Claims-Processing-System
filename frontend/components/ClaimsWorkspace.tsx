"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { getClaim } from "@/lib/api";
import type { DecisionTrace } from "@/lib/types";
import { DecisionTraceViewer } from "./DecisionTraceViewer";
import { ClaimForm } from "./ClaimForm";

export function ClaimsWorkspace() {
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [lookupId, setLookupId] = useState("");

  const lookupMutation = useMutation({
    mutationFn: getClaim,
    onSuccess: setTrace,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-10">
        <p className="text-sm font-semibold uppercase tracking-widest text-violet-700">Plum Claims AI</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Health insurance claims adjudication
        </h1>
        <p className="mt-3 max-w-3xl text-base text-slate-600">
          Submit a claim, inspect the full decision trace, and see exactly which pipeline stages
          passed, failed, or were skipped.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-6 text-lg font-semibold text-slate-900">Submit claim</h2>
          <ClaimForm onResult={setTrace} />
        </section>

        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">Lookup saved claim</h2>
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (lookupId.trim()) {
                  lookupMutation.mutate(lookupId.trim());
                }
              }}
            >
              <input
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="CLM_..."
                value={lookupId}
                onChange={(event) => setLookupId(event.target.value)}
              />
              <button
                type="submit"
                disabled={lookupMutation.isPending}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                Load
              </button>
            </form>
            {lookupMutation.isError && (
              <p className="mt-3 text-sm text-rose-600">
                {lookupMutation.error instanceof Error
                  ? lookupMutation.error.message
                  : "Claim not found"}
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
            <h2 className="mb-6 text-lg font-semibold text-slate-900">Decision trace</h2>
            {trace ? (
              <DecisionTraceViewer trace={trace} />
            ) : (
              <p className="text-sm text-slate-500">
                Submit a claim or load an existing claim ID to view the adjudication trace.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
