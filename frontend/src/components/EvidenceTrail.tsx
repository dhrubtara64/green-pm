"use client";

import type { EvidenceItem } from "@/lib/api";

const RELIABILITY_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  high:       { label: "High",       color: "text-emerald-400 bg-emerald-950/50 border-emerald-700/50", dot: "bg-emerald-400" },
  medium:     { label: "Medium",     color: "text-sky-400 bg-sky-950/50 border-sky-700/50",             dot: "bg-sky-400"     },
  low:        { label: "Low",        color: "text-amber-400 bg-amber-950/50 border-amber-700/50",       dot: "bg-amber-400"   },
  unverified: { label: "Unverified", color: "text-slate-400 bg-slate-800/50 border-slate-600/50",       dot: "bg-slate-400"   },
};

const SOURCE_LABELS: Record<string, string> = {
  document_folder: "Project Documents",
  document_upload: "Uploaded Document",
  schedule_xer: "P6 Schedule Export",
  boq_upload: "Bill of Quantities",
};

function relativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

interface EvidenceTrailProps {
  items: EvidenceItem[];
  highlightRefs?: string[];
}

export function EvidenceTrail({ items, highlightRefs = [] }: EvidenceTrailProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-10">
        <p className="text-slate-500 text-sm">No evidence linked to this activity yet.</p>
        <p className="text-slate-600 text-xs mt-1">Upload a document or schedule to populate the evidence trail.</p>
      </div>
    );
  }

  const supporting = items.filter(e => e.relation_type === "supports_progress_of");
  const contradicting = items.filter(e => e.relation_type === "contradicts");

  return (
    <div className="space-y-3">
      {contradicting.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-red-950/30 border border-red-700/40 mb-4">
          <span className="text-red-400">⚡</span>
          <span className="text-red-300 text-sm font-medium">
            {contradicting.length} contradicting source{contradicting.length > 1 ? "s" : ""} — human review required before reporting
          </span>
        </div>
      )}

      {contradicting.map(item => (
        <EvidenceCard key={item.id} item={item} highlighted={highlightRefs.includes(item.id)} />
      ))}
      {supporting.map(item => (
        <EvidenceCard key={item.id} item={item} highlighted={highlightRefs.includes(item.id)} />
      ))}
    </div>
  );
}

function EvidenceCard({ item, highlighted }: { item: EvidenceItem; highlighted: boolean }) {
  const isContradiction = item.relation_type === "contradicts";
  const reliability = RELIABILITY_CONFIG[item.source_reliability_signal] ?? RELIABILITY_CONFIG.unverified;
  const sourceLabel = SOURCE_LABELS[item.source_system] ?? item.source_system;

  return (
    <div className={`rounded-lg border p-4 transition-all ${
      highlighted
        ? "border-sky-500/60 bg-sky-950/20"
        : isContradiction
        ? "border-red-700/50 bg-red-950/20"
        : "border-slate-700 bg-slate-800/50"
    }`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          {isContradiction ? (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-red-400 bg-red-950/50 border border-red-700/50 px-2 py-0.5 rounded">
              <span>✕</span> Contradicts
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-700/50 px-2 py-0.5 rounded">
              <span>✓</span> Supports
            </span>
          )}
          <span className={`flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded border ${reliability.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${reliability.dot}`} />
            {reliability.label} reliability
          </span>
        </div>
        <span className="text-slate-500 text-xs whitespace-nowrap">{relativeTime(item.timestamp)}</span>
      </div>

      <p className="text-slate-200 text-sm leading-relaxed mb-3">
        {item.source_excerpt || item.extracted_content.slice(0, 300)}
      </p>

      <div className="flex items-center justify-between pt-3 border-t border-slate-700/50">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="text-slate-600">Sourced from:</span>
          <span className="text-slate-400">{sourceLabel}</span>
          {item.provenance_ref && (
            <>
              <span className="text-slate-700">·</span>
              <span className="font-mono text-slate-500 truncate max-w-xs" title={item.provenance_ref}>
                {item.provenance_ref.split("/").pop()}
              </span>
            </>
          )}
        </div>
        <span className="font-mono text-xs text-slate-600">{item.id}</span>
      </div>
    </div>
  );
}
