"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface ConfirmCorrectProps {
  activityId: string;
  fieldName: string;
  label: string;
  currentValue: string;
  displayValue: string;
  onUpdated: () => void;
}

export function ConfirmCorrect({
  activityId,
  fieldName,
  label,
  currentValue,
  displayValue,
  onUpdated,
}: ConfirmCorrectProps) {
  const [mode, setMode] = useState<"idle" | "correcting" | "loading" | "done">("idle");
  const [newValue, setNewValue] = useState(currentValue);
  const [rationale, setRationale] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  async function handleConfirm() {
    setMode("loading");
    try {
      await api.activities.confirm(activityId, fieldName, currentValue);
      setConfirmed(true);
      setMode("done");
      onUpdated();
    } catch {
      setMode("idle");
    }
  }

  async function handleCorrect() {
    if (!newValue.trim()) return;
    setMode("loading");
    try {
      await api.activities.correct(activityId, fieldName, currentValue, newValue, rationale || undefined);
      setMode("done");
      onUpdated();
    } catch {
      setMode("correcting");
    }
  }

  if (mode === "done") {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500">
        {confirmed
          ? <><span className="text-emerald-500">✓</span> Confirmed</>
          : <><span className="text-sky-500">✓</span> Correction logged</>
        }
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
          <p className="text-sm font-semibold text-slate-900 mt-0.5">{displayValue}</p>
        </div>
        {mode === "idle" && (
          <div className="flex gap-2 shrink-0">
            <button
              onClick={handleConfirm}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium
                         text-emerald-600 bg-emerald-50 hover:bg-emerald-100
                         border border-emerald-200 rounded-lg transition-colors"
            >
              <span>✓</span> Confirm
            </button>
            <button
              onClick={() => setMode("correcting")}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium
                         text-slate-600 bg-slate-50 hover:bg-slate-100
                         border border-slate-200 rounded-lg transition-colors"
            >
              <span>✎</span> Correct
            </button>
          </div>
        )}
      </div>

      {mode === "correcting" && (
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          <label className="block text-xs text-slate-500">Correct value</label>
          <input
            type="text"
            value={newValue}
            onChange={e => setNewValue(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded px-2.5 py-1.5
                       text-sm text-slate-900 focus:outline-none focus:border-sky-400"
          />
          <label className="block text-xs text-slate-500 mt-2">Reason (optional)</label>
          <input
            type="text"
            value={rationale}
            onChange={e => setRationale(e.target.value)}
            placeholder="e.g. Site walk confirmed actual 72%"
            className="w-full bg-white border border-slate-200 rounded px-2.5 py-1.5
                       text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-400"
          />
          <div className="flex gap-2 justify-end pt-1">
            <button
              onClick={() => setMode("idle")}
              className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
            <button
              onClick={handleCorrect}
              className="px-3 py-1.5 text-xs font-medium text-white bg-sky-600 hover:bg-sky-700
                         rounded-lg transition-colors"
            >
              Apply Correction
            </button>
          </div>
        </div>
      )}

      {mode === "loading" && (
        <p className="text-xs text-slate-400 mt-2">Saving...</p>
      )}
    </div>
  );
}
