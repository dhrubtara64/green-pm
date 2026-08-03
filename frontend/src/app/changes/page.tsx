"use client";

import { useEffect, useState } from "react";
import { api, type ChangeItem, type ChangesSummary } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  Open:     "bg-red-50 text-red-700 border border-red-200",
  Pending:  "bg-amber-50 text-amber-700 border border-amber-200",
  Closed:   "bg-green-50 text-green-700 border border-green-200",
  Approved: "bg-blue-50 text-blue-700 border border-blue-200",
};

const TYPE_STYLES: Record<string, string> = {
  NCR: "bg-red-100 text-red-800",
  RFI: "bg-purple-100 text-purple-800",
  VO:  "bg-emerald-100 text-emerald-800",
  TQ:  "bg-sky-100 text-sky-800",
  CO:  "bg-orange-100 text-orange-800",
};

const FLAG_STYLES: Record<string, string> = {
  critical: "text-red-600",
  warning:  "text-amber-600",
  info:     "text-blue-600",
};

export default function ChangesPage() {
  const [items, setItems] = useState<ChangeItem[]>([]);
  const [summary, setSummary] = useState<ChangesSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("All");

  useEffect(() => {
    async function load() {
      try {
        const [data, sum] = await Promise.all([api.changes.list(), api.changes.summary()]);
        setItems(data);
        setSummary(sum);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load change register");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const types = ["All", "NCR", "RFI", "VO", "TQ", "CO"];
  const filtered = filter === "All" ? items : items.filter(i => i.type === filter);

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Change Register</h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Bellary CCGT · NCRs, RFIs, Variation Orders, Technical Queries
        </p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mb-6">
          <KpiCard label="Total Items" value={summary.total} />
          <KpiCard label="Open" value={summary.open} warn={summary.open > 0} />
          <KpiCard label="Open NCRs" value={summary.open_ncrs} warn={summary.open_ncrs > 0} />
          <KpiCard label="Max Days Open" value={summary.max_days_open} warn={summary.max_days_open > 14} />
          <KpiCard label="Pending VO" value={summary.pending_vo_value} text />
          <KpiCard label="Approved VO" value={summary.approved_vo_value} text />
        </div>
      )}

      {/* AI summary banner */}
      <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
        <span className="font-semibold">⚡ AI Flag:</span>{" "}
        NCR-2024-E-041 is directly linked to WBS 5.1 — Carrot Controls &amp; Electrical&apos;s 78% claim cannot be
        substantiated until the CEIG pre-inspection NCR is closed. Recommend payment hold on that activity.
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        {types.map(t => (
          <button key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors
              ${filter === t
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}
          >{t}</button>
        ))}
      </div>

      {loading && <div className="text-slate-500 text-sm py-12 text-center">Loading change register...</div>}
      {error && <div className="text-red-600 text-sm py-4 px-4 bg-red-50 border border-red-200 rounded-lg">{error}</div>}

      {!loading && !error && (
        <div className="grid gap-3">
          {filtered.map(item => (
            <ChangeCard
              key={item.id}
              item={item}
              isExpanded={expanded === item.id}
              onToggle={() => setExpanded(expanded === item.id ? null : item.id)}
            />
          ))}
          {filtered.length === 0 && (
            <p className="text-slate-500 text-sm text-center py-8">No items for this filter.</p>
          )}
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, warn, text }: { label: string; value: string | number; warn?: boolean; text?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 ${warn ? "bg-red-50 border-red-200" : "bg-white border-slate-200"}`}>
      <div className={`font-bold ${text ? "text-base" : "text-xl"} ${warn ? "text-red-700" : "text-slate-900"}`}>
        {value}
      </div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}

function ChangeCard({ item, isExpanded, onToggle }: {
  item: ChangeItem;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const typeStyle = TYPE_STYLES[item.type] ?? "bg-slate-100 text-slate-700";
  const statusStyle = STATUS_STYLES[item.status] ?? "bg-slate-100 text-slate-600 border border-slate-200";
  const flagStyle = item.ai_flag_level ? (FLAG_STYLES[item.ai_flag_level] ?? "") : "";

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-start gap-3">
          <span className={`shrink-0 text-xs font-bold px-2 py-1 rounded ${typeStyle}`}>{item.type}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs text-slate-500">{item.id}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusStyle}`}>{item.status}</span>
              {item.ai_flag && (
                <span className={`text-xs font-medium ${flagStyle}`}>⚡ {item.ai_flag}</span>
              )}
            </div>
            <p className="text-slate-900 text-sm font-medium mt-1">{item.description}</p>
            {item.affected_activity_name && (
              <p className="text-slate-400 text-xs mt-0.5">Linked: {item.affected_activity_name}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            {item.value && (
              <div className="font-semibold text-sm text-slate-900">{item.value}</div>
            )}
            <div className="text-xs text-slate-400 mt-0.5">{item.days_open}d open</div>
            <div className="text-slate-400 mt-1">{isExpanded ? "▲" : "▼"}</div>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-100 px-4 py-4 bg-slate-50 grid gap-4 sm:grid-cols-2">
          {item.root_cause && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Root Cause</p>
              <p className="text-sm text-slate-700">{item.root_cause}</p>
            </div>
          )}
          {item.cost_impact && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Cost Impact</p>
              <p className="text-sm text-slate-700">{item.cost_impact}</p>
            </div>
          )}
          {item.timeline.length > 0 && (
            <div className="sm:col-span-2">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Timeline</p>
              <div className="grid gap-1">
                {item.timeline.map((t, i) => (
                  <div key={i} className="flex gap-3 text-xs text-slate-600">
                    <span className="font-mono shrink-0 text-slate-400">{t.date}</span>
                    <span>{t.event}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
