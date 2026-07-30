"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ActivitySummary } from "@/lib/api";
import { ScoreBadges, DivergenceBadge } from "@/components/ScoreBadges";

const DISCIPLINE_COLORS: Record<string, string> = {
  Civil:          "bg-stone-800 text-stone-300 border-stone-700",
  Mechanical:     "bg-blue-900/50 text-blue-300 border-blue-700/50",
  Piping:         "bg-cyan-900/50 text-cyan-300 border-cyan-700/50",
  Electrical:     "bg-yellow-900/50 text-yellow-300 border-yellow-700/50",
  "I&C":          "bg-purple-900/50 text-purple-300 border-purple-700/50",
  Commissioning:  "bg-rose-900/50 text-rose-300 border-rose-700/50",
};

export default function DashboardPage() {
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDiscipline, setFilterDiscipline] = useState<string>("All");
  const [filterFlag, setFilterFlag] = useState<string>("All");
  const [recomputing, setRecomputing] = useState(false);

  const disciplines = ["All", ...Array.from(new Set(activities.map(a => a.discipline).filter(Boolean))) as string[]];

  async function load() {
    try {
      setLoading(true);
      const data = await api.activities.list();
      setActivities(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load activities");
    } finally {
      setLoading(false);
    }
  }

  async function handleRecompute() {
    setRecomputing(true);
    try {
      await api.ingestion.recomputeAll();
      await load();
    } finally {
      setRecomputing(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = activities.filter(a => {
    if (filterDiscipline !== "All" && a.discipline !== filterDiscipline) return false;
    if (filterFlag === "Verification Required" && !a.verification_required) return false;
    if (filterFlag === "Low Confidence" && a.confidence_score >= 0.50) return false;
    if (filterFlag === "Divergent" && Math.abs(a.evidence_score - a.confidence_score) < 0.25) return false;
    return true;
  });

  const verificationCount = activities.filter(a => a.verification_required).length;
  const lowConfCount = activities.filter(a => a.confidence_score < 0.50).length;
  const divergentCount = activities.filter(a => Math.abs(a.evidence_score - a.confidence_score) >= 0.25).length;

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Project Progress</h1>
          <p className="text-slate-500 text-sm mt-1">
            Evidence-backed status sourced from your schedule and project documents
          </p>
        </div>
        <button
          onClick={handleRecompute}
          disabled={recomputing}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700
                     border border-slate-700 rounded-lg text-slate-300 transition-colors
                     disabled:opacity-50"
        >
          {recomputing ? "Recomputing..." : "↻ Recompute Scores"}
        </button>
      </div>

      {/* Summary chips */}
      {!loading && (
        <div className="flex flex-wrap gap-3 mb-6">
          <SummaryChip
            label="Total Activities"
            value={activities.length}
            color="text-slate-300 bg-slate-800 border-slate-700"
          />
          <SummaryChip
            label="Verification Required"
            value={verificationCount}
            color={verificationCount > 0 ? "text-red-300 bg-red-950/40 border-red-700/50" : "text-slate-400 bg-slate-800 border-slate-700"}
          />
          <SummaryChip
            label="Low Confidence (<50%)"
            value={lowConfCount}
            color={lowConfCount > 0 ? "text-amber-300 bg-amber-950/40 border-amber-700/50" : "text-slate-400 bg-slate-800 border-slate-700"}
          />
          <SummaryChip
            label="Evidence/Confidence Divergence"
            value={divergentCount}
            color={divergentCount > 0 ? "text-sky-300 bg-sky-950/40 border-sky-700/50" : "text-slate-400 bg-slate-800 border-slate-700"}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <FilterSelect
          label="Discipline"
          value={filterDiscipline}
          options={disciplines}
          onChange={setFilterDiscipline}
        />
        <FilterSelect
          label="Flag"
          value={filterFlag}
          options={["All", "Verification Required", "Low Confidence", "Divergent"]}
          onChange={setFilterFlag}
        />
      </div>

      {loading && (
        <div className="text-slate-500 text-sm py-12 text-center">Loading activities...</div>
      )}
      {error && (
        <div className="text-red-400 text-sm py-4 bg-red-950/20 border border-red-700/30 rounded-lg px-4">
          {error}
        </div>
      )}

      {/* Activity grid */}
      {!loading && !error && (
        <div className="grid gap-3">
          {filtered.map(activity => (
            <ActivityRow key={activity.id} activity={activity} />
          ))}
          {filtered.length === 0 && (
            <p className="text-slate-500 text-sm text-center py-8">No activities match the current filter.</p>
          )}
        </div>
      )}
    </div>
  );
}

function SummaryChip({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${color}`}>
      <span className="font-bold text-base">{value}</span>
      <span className="text-xs opacity-80">{label}</span>
    </div>
  );
}

function FilterSelect({
  label, value, options, onChange
}: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500">{label}:</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="text-sm bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5
                   text-slate-300 focus:outline-none focus:border-slate-600"
      >
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

function ActivityRow({ activity }: { activity: ActivitySummary }) {
  const disciplineColor = DISCIPLINE_COLORS[activity.discipline ?? ""] ?? "bg-slate-800 text-slate-400 border-slate-700";

  return (
    <Link
      href={`/activities/${activity.id}`}
      className="block rounded-xl border border-slate-800 bg-slate-900 hover:border-slate-700
                 hover:bg-slate-800/50 transition-all p-4 group"
    >
      <div className="flex items-start gap-4">
        {/* WBS + Name */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            {activity.wbs_ref && (
              <span className="font-mono text-xs text-slate-600">{activity.wbs_ref}</span>
            )}
            {activity.discipline && (
              <span className={`text-xs px-2 py-0.5 rounded border ${disciplineColor}`}>
                {activity.discipline}
              </span>
            )}
            {activity.verification_required && (
              <span className="flex items-center gap-1 text-xs text-red-400 bg-red-950/50 border border-red-700/50 px-2 py-0.5 rounded font-medium">
                <span>⚡</span> Verification Required
              </span>
            )}
          </div>
          <p className="text-white font-medium text-sm group-hover:text-gpm-green transition-colors">
            {activity.name}
          </p>
          {activity.missing_evidence && (
            <p className="text-amber-400/70 text-xs mt-1.5 truncate">
              Missing: {activity.missing_evidence}
            </p>
          )}
        </div>

        {/* Progress % */}
        <div className="text-right shrink-0">
          <div className="text-lg font-bold text-white">{Math.round(activity.reported_progress)}%</div>
          <div className="text-xs text-slate-500">Reported</div>
        </div>

        {/* Score badges */}
        <div className="shrink-0 w-56">
          <ScoreBadges
            evidenceScore={activity.evidence_score}
            confidenceScore={activity.confidence_score}
            compact={false}
          />
          <div className="mt-2">
            <DivergenceBadge
              evidenceScore={activity.evidence_score}
              confidenceScore={activity.confidence_score}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}
