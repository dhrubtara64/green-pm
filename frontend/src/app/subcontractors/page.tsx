"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ActivitySummary } from "@/lib/api";

const SUB_COLORS: Record<string, string> = {
  "Mango Civil Works":           "bg-orange-50 border-orange-200 text-orange-800",
  "Brinjal Mechanical Systems":  "bg-purple-50 border-purple-200 text-purple-800",
  "Carrot Controls & Electrical":"bg-amber-50 border-amber-200 text-amber-800",
  "Avocado Automation":          "bg-green-50 border-green-200 text-green-800",
  "Guava Power Services":        "bg-rose-50 border-rose-200 text-rose-800",
  "Turnip Engineering":          "bg-slate-50 border-slate-300 text-slate-700",
};

const SUB_ICONS: Record<string, string> = {
  "Mango Civil Works":           "🥭",
  "Brinjal Mechanical Systems":  "🍆",
  "Carrot Controls & Electrical":"🥕",
  "Avocado Automation":          "🥑",
  "Guava Power Services":        "🍈",
  "Turnip Engineering":          "🌿",
};

type SubGroup = {
  name: string;
  activities: ActivitySummary[];
  avgEvidence: number;
  avgConfidence: number;
  flagCount: number;
};

export default function SubcontractorsPage() {
  const [groups, setGroups] = useState<SubGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.activities.list();
        const map = new Map<string, ActivitySummary[]>();
        for (const a of data) {
          const key = a.subcontractor ?? "Unassigned";
          if (!map.has(key)) map.set(key, []);
          map.get(key)!.push(a);
        }
        const built: SubGroup[] = [];
        for (const [name, acts] of Array.from(map.entries())) {
          built.push({
            name,
            activities: acts,
            avgEvidence: acts.reduce((s, a) => s + a.evidence_score, 0) / acts.length,
            avgConfidence: acts.reduce((s, a) => s + a.confidence_score, 0) / acts.length,
            flagCount: acts.filter(a => a.verification_required).length,
          });
        }
        built.sort((a, b) => b.flagCount - a.flagCount || a.name.localeCompare(b.name));
        setGroups(built);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totalFlags = groups.reduce((s, g) => s + g.flagCount, 0);

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Subcontractor Watch</h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Bellary CCGT · Evidence &amp; confidence by package
        </p>
      </div>

      {!loading && totalFlags > 0 && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
          <span className="font-semibold">⚡ {totalFlags} activit{totalFlags === 1 ? "y" : "ies"} flagged</span>{" "}
          across packages — review verification-required items before next payment milestone.
        </div>
      )}

      {loading && <div className="text-slate-500 text-sm py-12 text-center">Loading subcontractor data...</div>}
      {error && <div className="text-red-600 text-sm py-4 px-4 bg-red-50 border border-red-200 rounded-lg">{error}</div>}

      {!loading && !error && (
        <div className="grid gap-5">
          {groups.map(group => <SubGroup key={group.name} group={group} />)}
        </div>
      )}
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.7 ? "bg-green-500" : score >= 0.45 ? "bg-amber-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-20 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-semibold text-slate-700 w-8 text-right">{pct}%</span>
    </div>
  );
}

function SubGroup({ group }: { group: SubGroup }) {
  const colorClass = SUB_COLORS[group.name] ?? "bg-slate-50 border-slate-200 text-slate-700";
  const icon = SUB_ICONS[group.name] ?? "🏗";
  const [open, setOpen] = useState(false);

  return (
    <div className={`rounded-xl border overflow-hidden ${colorClass}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:opacity-90 transition-opacity"
      >
        <span className="text-2xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">{group.name}</span>
            {group.flagCount > 0 && (
              <span className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                ⚡ {group.flagCount} flag{group.flagCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="mt-2 grid gap-1.5 max-w-xs">
            <ScoreBar label="Evidence" score={group.avgEvidence} />
            <ScoreBar label="Confidence" score={group.avgConfidence} />
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold">{group.activities.length}</div>
          <div className="text-xs opacity-70">activities</div>
          <div className="mt-2 text-xs opacity-60">{open ? "▲ Hide" : "▼ Show"}</div>
        </div>
      </button>

      {open && (
        <div className="border-t border-current border-opacity-10 bg-white">
          <div className="grid gap-0">
            {group.activities.map((a, i) => (
              <Link
                key={a.id}
                href={`/activities/${a.id}`}
                className={`flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors text-sm
                  ${i > 0 ? "border-t border-slate-100" : ""}`}
              >
                {a.wbs_ref && <span className="font-mono text-xs text-slate-400 w-14 shrink-0">{a.wbs_ref}</span>}
                <span className="flex-1 min-w-0 text-slate-800 truncate">{a.name}</span>
                {a.verification_required && (
                  <span className="text-xs text-red-600 font-medium shrink-0">⚡ Verify</span>
                )}
                <span className="font-bold text-slate-700 shrink-0">{Math.round(a.reported_progress)}%</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
