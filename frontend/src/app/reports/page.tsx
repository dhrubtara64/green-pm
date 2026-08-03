"use client";

import { useEffect, useState } from "react";
import { api, type Report } from "@/lib/api";

export default function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafting, setDrafting] = useState(false);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendDone, setSendDone] = useState(false);
  const [edited, setEdited] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const list = await api.reports.list();
      setReports(list);
      if (list.length > 0) {
        setReport(list[0]);
        setContent(list[0].edited_content ?? list[0].draft_content);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleDraft() {
    setDrafting(true);
    try {
      await api.reports.draft();
    } finally {
      setDrafting(false);
      setEdited(false);
      setSendDone(false);
      await load();
    }
  }

  async function handleSave() {
    if (!report) return;
    setSaving(true);
    try {
      const updated = await api.reports.edit(report.id, content);
      setReport(updated);
      setEdited(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleSend() {
    if (!report) return;
    setSending(true);
    try {
      await api.reports.send(report.id);
      setSendDone(true);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Weekly Report</h1>
          <p className="text-slate-500 text-sm mt-1">
            Green PM AI drafts from current project evidence — you review, edit, and confirm before sending.
          </p>
        </div>
        <button
          onClick={handleDraft}
          disabled={drafting}
          className="flex items-center gap-2 px-4 py-2 bg-gpm-green/10 hover:bg-gpm-green/20
                     border border-gpm-green/30 text-gpm-green rounded-lg text-sm font-medium
                     transition-colors disabled:opacity-50"
        >
          {drafting ? "Drafting..." : "Generate New Draft"}
        </button>
      </div>

      {loading && <p className="text-slate-500 text-sm py-8 text-center">Loading...</p>}

      {!loading && !report && (
        <div className="text-center py-16 border-2 border-dashed border-slate-200 rounded-xl">
          <p className="text-slate-500 text-sm">No reports yet.</p>
          <p className="text-slate-400 text-xs mt-1">Click &quot;Generate New Draft&quot; to create one from current project evidence.</p>
        </div>
      )}

      {!loading && report && (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-4 py-2.5 rounded-lg bg-white border border-slate-200">
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span>Generated: {new Date(report.created_at).toLocaleString()}</span>
              {report.confirmed_at && (
                <span className="text-emerald-600">Sent (logged): {new Date(report.confirmed_at).toLocaleString()}</span>
              )}
              {edited && <span className="text-amber-600">Unsaved changes</span>}
            </div>
            <div className="flex gap-2">
              {edited && (
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 border border-slate-200
                             text-slate-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Edits"}
                </button>
              )}
              {sendDone ? (
                <span className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-emerald-600
                                 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <span>✓</span> Send action logged
                </span>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={sending}
                  className="px-3 py-1.5 text-xs font-medium bg-gpm-green/10 hover:bg-gpm-green/20
                             border border-gpm-green/30 text-gpm-green rounded-lg
                             transition-colors disabled:opacity-50"
                >
                  {sending ? "Logging..." : "Send →"}
                </button>
              )}
            </div>
          </div>

          <div className="px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            ⚠ &quot;Send&quot; logs the action and records your confirmation. No email is sent in this version — all outbound communication is your responsibility.
          </div>

          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">Report Draft (editable)</span>
              {report.edited_content && !edited && (
                <span className="text-xs text-slate-400">Showing your edited version</span>
              )}
            </div>
            <textarea
              value={content}
              onChange={e => { setContent(e.target.value); setEdited(true); }}
              className="w-full h-[600px] bg-transparent p-5 text-sm text-slate-700 font-mono leading-relaxed
                         resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>

          {reports.length > 1 && (
            <div className="mt-6">
              <h2 className="text-xs text-slate-500 uppercase tracking-wide mb-2">Previous Reports</h2>
              <div className="space-y-1">
                {reports.slice(1).map(r => (
                  <button
                    key={r.id}
                    onClick={() => {
                      setReport(r);
                      setContent(r.edited_content ?? r.draft_content);
                      setEdited(false);
                      setSendDone(!!r.confirmed_at);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors
                                ${report.id === r.id
                      ? "bg-slate-100 text-slate-700"
                      : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {new Date(r.created_at).toLocaleString()}
                    {r.confirmed_at && <span className="ml-2 text-emerald-600">· Sent</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
