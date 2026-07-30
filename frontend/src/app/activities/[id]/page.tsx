"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ActivityDetail } from "@/lib/api";
import { ScoreBadges, DivergenceBadge } from "@/components/ScoreBadges";
import { EvidenceTrail } from "@/components/EvidenceTrail";
import { ConfirmCorrect } from "@/components/ConfirmCorrect";
import { ChatPanel } from "@/components/ChatPanel";

export default function ActivityPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [activity, setActivity] = useState<ActivityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);
  const [highlightedRefs, setHighlightedRefs] = useState<string[]>([]);
  const [recomputing, setRecomputing] = useState(false);

  async function load() {
    try {
      const data = await api.activities.get(id);
      setActivity(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load activity");
    } finally {
      setLoading(false);
    }
  }

  async function handleRecompute() {
    setRecomputing(true);
    try {
      await api.activities.recompute(id);
      await load();
    } finally {
      setRecomputing(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  if (loading) {
    return <div className="p-8 text-slate-500 text-sm">Loading activity...</div>;
  }
  if (error || !activity) {
    return (
      <div className="p-8">
        <p className="text-red-600 text-sm">{error || "Activity not found"}</p>
        <Link href="/" className="text-slate-500 hover:text-slate-900 text-sm mt-3 inline-block">← Back to Dashboard</Link>
      </div>
    );
  }

  const progressPct = `${Math.round(activity.reported_progress)}%`;

  return (
    <div className="flex h-full">
      <div className={`flex-1 overflow-y-auto transition-all ${showChat ? "max-w-[calc(100%-380px)]" : ""}`}>
        <div className="p-6 max-w-4xl">
          <div className="flex items-center gap-3 mb-6">
            <Link href="/" className="text-slate-500 hover:text-slate-700 text-sm">← Dashboard</Link>
            {activity.wbs_ref && (
              <span className="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                {activity.wbs_ref}
              </span>
            )}
          </div>

          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex-1">
              <h1 className="text-xl font-bold text-slate-900 mb-1">{activity.name}</h1>
              {activity.discipline && (
                <span className="text-xs text-slate-500">{activity.discipline}</span>
              )}
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={handleRecompute}
                disabled={recomputing}
                className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg
                           text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
              >
                {recomputing ? "Recomputing..." : "↻ Recompute"}
              </button>
              <button
                onClick={() => setShowChat(prev => !prev)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg
                            border transition-colors ${showChat
                  ? "bg-gpm-green/10 border-gpm-green/40 text-gpm-green"
                  : "bg-white border-slate-200 text-slate-700 hover:text-slate-900"
                }`}
              >
                <span className="text-base">◎</span>
                Green PM AI
              </button>
            </div>
          </div>

          {activity.verification_required && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 mb-6">
              <span className="text-red-500 text-lg shrink-0">⚡</span>
              <div>
                <p className="text-red-700 font-semibold text-sm">Verification Required</p>
                <p className="text-red-500 text-xs mt-0.5">
                  Contradicting or insufficient evidence detected. Human review is required before reporting this activity&apos;s status.
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Reported Progress</p>
              <p className="text-3xl font-bold text-slate-900">{progressPct}</p>
              <p className="text-xs text-slate-400 mt-1">Sourced from your schedule</p>
            </div>

            <div className="col-span-2 rounded-xl border border-slate-200 bg-white p-4">
              <ScoreBadges
                evidenceScore={activity.evidence_score}
                confidenceScore={activity.confidence_score}
              />
              <div className="mt-3">
                <DivergenceBadge
                  evidenceScore={activity.evidence_score}
                  confidenceScore={activity.confidence_score}
                />
              </div>
            </div>
          </div>

          {activity.confidence_reasoning && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 mb-6">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Green PM AI Assessment</p>
              <p className="text-slate-700 text-sm leading-relaxed">{activity.confidence_reasoning}</p>
            </div>
          )}

          {activity.missing_evidence && (
            <div className="flex items-start gap-3 p-4 rounded-xl border border-amber-200 bg-amber-50 mb-6">
              <span className="text-amber-500 shrink-0">◌</span>
              <div>
                <p className="text-amber-700 text-xs font-semibold uppercase tracking-wide mb-1">Missing Evidence</p>
                <p className="text-amber-700 text-sm">{activity.missing_evidence}</p>
              </div>
            </div>
          )}

          <div className="mb-6">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Confirm or Correct
            </h2>
            <div className="space-y-3">
              <ConfirmCorrect
                activityId={activity.id}
                fieldName="reported_progress"
                label="Reported Progress"
                currentValue={String(activity.reported_progress)}
                displayValue={progressPct}
                onUpdated={load}
              />
              <ConfirmCorrect
                activityId={activity.id}
                fieldName="confidence_score"
                label="Confidence Score"
                currentValue={String(activity.confidence_score)}
                displayValue={`${Math.round(activity.confidence_score * 100)}% — ${activity.confidence_reasoning?.slice(0, 80) ?? "No reasoning yet"}...`}
                onUpdated={load}
              />
              {activity.missing_evidence && (
                <ConfirmCorrect
                  activityId={activity.id}
                  fieldName="missing_evidence"
                  label="Missing Evidence Gap"
                  currentValue={activity.missing_evidence}
                  displayValue={activity.missing_evidence}
                  onUpdated={load}
                />
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                Evidence Trail
                <span className="ml-2 text-slate-400 font-normal normal-case">
                  ({activity.evidence_items.length} source{activity.evidence_items.length !== 1 ? "s" : ""})
                </span>
              </h2>
            </div>
            <EvidenceTrail items={activity.evidence_items} highlightRefs={highlightedRefs} />
          </div>
        </div>
      </div>

      {showChat && (
        <div className="w-[380px] shrink-0 border-l border-slate-200 h-full">
          <ChatPanel
            activity={activity}
            onClose={() => setShowChat(false)}
            highlightRef={setHighlightedRefs}
          />
        </div>
      )}
    </div>
  );
}
