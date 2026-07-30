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
    await api.activities.confirm(activityId, fieldName, currentValue);
    setConfirmed(true);
    setMode("done");
    onUpdated();
  }

  async function handleCorrect() {
    if (!newValue.trim()) return;
    setMode("loading");
    await api.activities.correct(activityId, fieldName, currentValue, newValue, rationale || undefined);
    setMode("done");
    onUpdated();
  }

  if (mode === "done") {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400">
        {confirmed
          ? <><span className="text-emerald-400">✓</span> Confirmed</>
          : <><span className="text-sky-400">✓</span> Correction logged</>
        }
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/30 p-3">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
          <p className="text-sm font-semibold text-white mt-0.5">{displayValue}</p>
        </div>
        {mode === "idle" && (
          <div className="flex gap-2 shrink-0">
            <button
              onClick={handleConfirm}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium
                         text-emerald-400 bg-emerald-950/40 hover:bg-emerald-950/70
                         border border-emerald-700/50 rounded-lg transition-colors"
            >
              <span>✓</span> Confirm
            </button>
            <button
              onClick={() => setMode("correcting")}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium
                         text-slate-300 bg-slate-700/40 hover:bg-slate-700/70
                         border border-slate-600 rounded-lg transition-colors"
            >
              <span>✎</span> Correct
            </button>
          </div>
        )}
      </div>

      {mode === "correcting" && (
        <div className="mt-3 space-y-2 border-t border-slate-700 pt-3">
          <label className="block text-xs text-slate-400">Correct value</label>
          <input
            type="text"
            value={newValue}
            onChange={e => setNewValue(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded px-2.5 py-1.5
                       text-sm text-white focus:outline-none focus:border-sky-500/50"
          />
          <label className="block text-xs text-slate-400 mt-2">Reason (optional)</label>
          <input
            type="text"
            value={rationale}
            onChange={e => setRationale(e.target.value)}
            placeholder="e.g. Site walk confirmed actual 72%"
            className="w-full bg-slate-900 border border-slate-600 rounded px-2.5 py-1.5
                       text-sm text-white placeholder-slate-600 focus:outline-none focus:border-sky-500/50"
          />
          <div className="flex gap-2 justify-end pt-1">
            <button
              onClick={() => setMode("idle")}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              onClick={handleCorrect}
              className="px-3 py-1.5 text-xs font-medium text-white bg-sky-700 hover:bg-sky-600
                         rounded-lg transition-colors"
            >
              Apply Correction
            </button>
          </div>
        </div>
      )}

      {mode === "loading" && (
        <p className="text-xs text-slate-500 mt-2">Saving...</p>
      )}
    </div>
  );
}
