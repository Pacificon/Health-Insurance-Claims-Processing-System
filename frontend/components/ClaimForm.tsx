"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getPolicySummary, submitClaim } from "@/lib/api";
import type {
  ClaimCategory,
  ClaimDocument,
  ClaimSubmission,
  DecisionTrace,
  DocumentType,
  TestCasePreset,
} from "@/lib/types";

const CLAIM_CATEGORIES: ClaimCategory[] = [
  "CONSULTATION",
  "DIAGNOSTIC",
  "PHARMACY",
  "DENTAL",
  "VISION",
  "ALTERNATIVE_MEDICINE",
];

const DOCUMENT_TYPES: DocumentType[] = [
  "PRESCRIPTION",
  "HOSPITAL_BILL",
  "PHARMACY_BILL",
  "LAB_REPORT",
  "DIAGNOSTIC_REPORT",
  "DENTAL_REPORT",
  "DISCHARGE_SUMMARY",
];

function emptyDocument(index: number): ClaimDocument {
  return {
    file_id: `F${String(index).padStart(3, "0")}`,
    file_name: "",
    actual_type: "PRESCRIPTION",
    quality: "GOOD",
  };
}

const DEFAULT_SUBMISSION: ClaimSubmission = {
  member_id: "EMP001",
  policy_id: "PLUM_GHI_2024",
  claim_category: "CONSULTATION",
  treatment_date: "2024-11-01",
  claimed_amount: 1500,
  documents: [emptyDocument(1), emptyDocument(2)],
};

interface ClaimFormProps {
  onResult: (trace: DecisionTrace) => void;
}

export function ClaimForm({ onResult }: ClaimFormProps) {
  const [form, setForm] = useState<ClaimSubmission>(DEFAULT_SUBMISSION);
  const [presets, setPresets] = useState<TestCasePreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [contentJsonByDoc, setContentJsonByDoc] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const policyQuery = useQuery({
    queryKey: ["policy-summary"],
    queryFn: getPolicySummary,
  });

  useEffect(() => {
    fetch("/test_cases.json")
      .then((response) => response.json())
      .then((data: { test_cases: TestCasePreset[] }) => setPresets(data.test_cases))
      .catch(() => setPresets([]));
  }, []);

  const mutation = useMutation({
    mutationFn: submitClaim,
    onSuccess: onResult,
  });

  function updateField<K extends keyof ClaimSubmission>(key: K, value: ClaimSubmission[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateDocument(index: number, patch: Partial<ClaimDocument>) {
    setForm((current) => ({
      ...current,
      documents: current.documents.map((doc, docIndex) =>
        docIndex === index ? { ...doc, ...patch } : doc,
      ),
    }));
  }

  function addDocument() {
    setForm((current) => ({
      ...current,
      documents: [...current.documents, emptyDocument(current.documents.length + 1)],
    }));
  }

  function removeDocument(index: number) {
    setForm((current) => ({
      ...current,
      documents: current.documents.filter((_, docIndex) => docIndex !== index),
    }));
  }

  function loadPreset(caseId: string) {
    const preset = presets.find((item) => item.case_id === caseId);
    if (!preset) return;

    setForm(preset.input);
    setSelectedPreset(caseId);

    const jsonMap: Record<string, string> = {};
    for (const doc of preset.input.documents) {
      if (doc.content) {
        jsonMap[doc.file_id] = JSON.stringify(doc.content, null, 2);
      }
    }
    setContentJsonByDoc(jsonMap);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);

    let documents: ClaimDocument[];
    try {
      documents = form.documents.map((doc) => {
        const raw = contentJsonByDoc[doc.file_id]?.trim();
        if (!raw) {
          return { ...doc, content: undefined };
        }
        return { ...doc, content: JSON.parse(raw) as Record<string, unknown> };
      });
    } catch {
      setFormError("One or more document content JSON fields are invalid.");
      return;
    }

    mutation.mutate({ ...form, documents });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-xl border border-violet-100 bg-violet-50/60 p-4">
        <label className="block text-sm font-medium text-slate-700">Load test case preset</label>
        <select
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          value={selectedPreset}
          onChange={(event) => loadPreset(event.target.value)}
        >
          <option value="">Custom claim</option>
          {presets.map((preset) => (
            <option key={preset.case_id} value={preset.case_id}>
              {preset.case_id} — {preset.case_name}
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs text-slate-600">
          Presets include embedded extraction content for eval scenarios. Custom claims need document
          metadata only unless JSON content is provided.
        </p>
      </div>

      {policyQuery.data && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <span className="font-medium text-slate-800">{policyQuery.data.policy_name}</span>
          <span className="mx-2">·</span>
          Per-claim limit {policyQuery.data.per_claim_limit.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Member ID</span>
          <input
            required
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.member_id}
            onChange={(event) => updateField("member_id", event.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Policy ID</span>
          <input
            required
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.policy_id}
            onChange={(event) => updateField("policy_id", event.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Claim category</span>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.claim_category}
            onChange={(event) => updateField("claim_category", event.target.value as ClaimCategory)}
          >
            {CLAIM_CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Treatment date</span>
          <input
            required
            type="date"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.treatment_date}
            onChange={(event) => updateField("treatment_date", event.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Claimed amount (₹)</span>
          <input
            required
            type="number"
            min={1}
            step={1}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.claimed_amount}
            onChange={(event) => updateField("claimed_amount", Number(event.target.value))}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Hospital name (optional)</span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.hospital_name ?? ""}
            onChange={(event) => updateField("hospital_name", event.target.value || undefined)}
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={form.simulate_component_failure ?? false}
          onChange={(event) => updateField("simulate_component_failure", event.target.checked)}
        />
        Simulate component failure (TC011)
      </label>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Documents</h3>
          <button
            type="button"
            onClick={addDocument}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Add document
          </button>
        </div>

        {form.documents.map((doc, index) => (
          <div key={`${doc.file_id}-${index}`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <p className="font-medium text-slate-800">Document {index + 1}</p>
              {form.documents.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeDocument(index)}
                  className="text-sm text-rose-600 hover:text-rose-700"
                >
                  Remove
                </button>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">File ID</span>
                <input
                  required
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={doc.file_id}
                  onChange={(event) => updateDocument(index, { file_id: event.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">File name</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={doc.file_name ?? ""}
                  onChange={(event) => updateDocument(index, { file_name: event.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Document type</span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={doc.actual_type}
                  onChange={(event) =>
                    updateDocument(index, { actual_type: event.target.value as DocumentType })
                  }
                >
                  {DOCUMENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Quality</span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={doc.quality ?? ""}
                  onChange={(event) =>
                    updateDocument(index, {
                      quality: event.target.value ? (event.target.value as "GOOD" | "UNREADABLE") : undefined,
                    })
                  }
                >
                  <option value="">Not set</option>
                  <option value="GOOD">GOOD</option>
                  <option value="UNREADABLE">UNREADABLE</option>
                </select>
              </label>
              <label className="block text-sm sm:col-span-2">
                <span className="font-medium text-slate-700">Patient name on document</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={doc.patient_name_on_doc ?? ""}
                  onChange={(event) =>
                    updateDocument(index, { patient_name_on_doc: event.target.value || undefined })
                  }
                />
              </label>
              <label className="block text-sm sm:col-span-2">
                <span className="font-medium text-slate-700">Extraction content JSON (eval bypass)</span>
                <textarea
                  rows={4}
                  placeholder='{"patient_name": "Rajesh Kumar", ...}'
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
                  value={contentJsonByDoc[doc.file_id] ?? ""}
                  onChange={(event) =>
                    setContentJsonByDoc((current) => ({
                      ...current,
                      [doc.file_id]: event.target.value,
                    }))
                  }
                />
              </label>
            </div>
          </div>
        ))}
      </div>

      {(formError || mutation.isError) && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {formError ??
            (mutation.error instanceof Error ? mutation.error.message : "Submission failed")}
        </div>
      )}

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full rounded-xl bg-violet-700 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {mutation.isPending ? "Processing claim…" : "Submit claim"}
      </button>
    </form>
  );
}
