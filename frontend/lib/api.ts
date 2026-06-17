import type { ClaimSubmission, DecisionTrace, PolicySummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export function submitClaim(submission: ClaimSubmission): Promise<DecisionTrace> {
  return request<DecisionTrace>("/claims", {
    method: "POST",
    body: JSON.stringify(submission),
  });
}

export function getClaim(claimId: string): Promise<DecisionTrace> {
  return request<DecisionTrace>(`/claims/${encodeURIComponent(claimId)}`);
}

export function getPolicySummary(): Promise<PolicySummary> {
  return request<PolicySummary>("/policy/summary");
}
