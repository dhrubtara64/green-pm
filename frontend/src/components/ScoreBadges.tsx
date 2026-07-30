"use client";

interface ScoreBarProps {
  value: number;
  label: string;
  colorClass: string;
  tooltip: string;
}

function ScoreBar({ value, label, colorClass, tooltip }: ScoreBarProps) {
  const pct = Math.round(value * 100);
  return (
    <div className="group relative">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</span>
        <span className="text-sm font-bold text-white">{pct}%</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10
                      bg-slate-900 border border-slate-600 rounded px-3 py-2 text-xs text-slate-300
                      whitespace-nowrap shadow-lg max-w-xs">
        {tooltip}
      </div>
    </div>
  );
}

function scoreColor(value: number, type: "evidence" | "confidence") {
  if (type === "evidence") {
    if (value >= 0.65) return "bg-emerald-500";
    if (value >= 0.35) return "bg-amber-500";
    return "bg-red-500";
  }
  if (value >= 0.65) return "bg-sky-500";
  if (value >= 0.35) return "bg-amber-400";
  return "bg-orange-500";
}

interface ScoreBadgesProps {
  evidenceScore: number;
  confidenceScore: number;
  compact?: boolean;
}

export function ScoreBadges({ evidenceScore, confidenceScore, compact = false }: ScoreBadgesProps) {
  if (compact) {
    const evPct = Math.round(evidenceScore * 100);
    const confPct = Math.round(confidenceScore * 100);
    return (
      <div className="flex gap-3 items-center">
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Evidence</span>
          <span className={`text-sm font-bold px-2 py-0.5 rounded ${
            evidenceScore >= 0.65 ? "text-emerald-400" : evidenceScore >= 0.35 ? "text-amber-400" : "text-red-400"
          }`}>{evPct}%</span>
        </div>
        <div className="w-px h-8 bg-slate-700" />
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Confidence</span>
          <span className={`text-sm font-bold px-2 py-0.5 rounded ${
            confidenceScore >= 0.65 ? "text-sky-400" : confidenceScore >= 0.35 ? "text-amber-400" : "text-orange-400"
          }`}>{confPct}%</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <ScoreBar
        value={evidenceScore}
        label="Evidence Score"
        colorClass={scoreColor(evidenceScore, "evidence")}
        tooltip="Objective: how many independent sources support this activity, how recent they are, and whether they agree. Computed without AI judgment."
      />
      <ScoreBar
        value={confidenceScore}
        label="Confidence Score"
        colorClass={scoreColor(confidenceScore, "confidence")}
        tooltip="AI-calibrated belief in this activity's true status — additionally weighing source reliability history and interpretive ambiguity. Distinct from Evidence Score."
      />
    </div>
  );
}

export function DivergenceBadge({ evidenceScore, confidenceScore }: { evidenceScore: number; confidenceScore: number }) {
  const gap = Math.abs(evidenceScore - confidenceScore);
  if (gap < 0.25) return null;

  const isLowConf = confidenceScore < evidenceScore;
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-amber-950/50 border border-amber-700/50">
      <span className="text-amber-400 text-xs">⚠</span>
      <span className="text-amber-300 text-xs font-medium">
        {isLowConf
          ? "Evidence strong — source reliability concern"
          : "Confident despite thin evidence — investigate why"}
      </span>
    </div>
  );
}
