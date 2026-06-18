import type { ClaimSubmission, DecisionTrace, PolicySummary } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new Error(
      `Cannot reach API at ${API_BASE}. Start the backend with: uvicorn app.main:app --reload --app-dir . --port 8001`,
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : typeof body.error === "string"
          ? body.error
          : response.statusText;

    if (detail.includes("URL") && detail.includes("not found")) {
      throw new Error(
        `${detail} The UI called ${url}, which is not the Plum claims API. ` +
          `Set NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 in frontend/.env.local and restart npm run dev.`,
      );
    }

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
