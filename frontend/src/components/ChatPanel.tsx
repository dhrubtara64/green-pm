"use client";

import { useState, useRef, useEffect } from "react";
import { api, type ChatMessage, type ActivityDetail } from "@/lib/api";

interface ChatPanelProps {
  activity: ActivityDetail;
  onClose: () => void;
  highlightRef?: (refs: string[]) => void;
}

export function ChatPanel({ activity, onClose, highlightRef }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const SUGGESTED_QUESTIONS = [
    "Why is this activity's confidence score low?",
    "What evidence supports the reported progress?",
    "What's missing for this activity?",
    "Are there any contradictions in the evidence?",
  ];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await api.chat.send(activity.id, text, messages);
      const assistantMsg: ChatMessage = { role: "assistant", content: response.answer };
      setMessages(prev => [...prev, assistantMsg]);
      if (highlightRef && response.evidence_refs?.length) {
        highlightRef(response.evidence_refs);
      }
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Green PM AI is temporarily unavailable. Please try again.",
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-200">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-gpm-green/10 border border-gpm-green/30 flex items-center justify-center">
            <span className="text-gpm-green text-xs font-bold">G</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Green PM AI</p>
            <p className="text-xs text-slate-500 truncate max-w-[180px]">{activity.name}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-700 text-lg leading-none"
        >
          ✕
        </button>
      </div>

      <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
        <p className="text-xs text-slate-500">
          Focused on this activity only. For project-wide questions, use the dashboard.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-slate-500 text-sm">Ask about this activity&apos;s evidence and confidence:</p>
            {SUGGESTED_QUESTIONS.map(q => (
              <button
                key={q}
                onClick={() => send(q)}
                className="w-full text-left text-sm text-slate-700 bg-slate-50 hover:bg-slate-100
                           border border-slate-200 hover:border-slate-300 rounded-lg px-3 py-2.5
                           transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-lg px-3 py-2.5 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-gpm-green/10 text-slate-900 border border-gpm-green/20"
                : "bg-slate-50 text-slate-700 border border-slate-200"
            }`}>
              {msg.role === "assistant" && (
                <p className="text-xs text-slate-400 mb-1 font-medium">Green PM AI</p>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5">
              <p className="text-xs text-slate-400 mb-1">Green PM AI</p>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send(input)}
            placeholder="Ask about evidence or confidence..."
            className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm
                       text-slate-900 placeholder-slate-400 focus:outline-none focus:border-gpm-green/50
                       focus:ring-1 focus:ring-gpm-green/20"
            disabled={loading}
          />
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            className="px-3 py-2 bg-gpm-green/10 hover:bg-gpm-green/20 border border-gpm-green/30
                       text-gpm-green rounded-lg text-sm font-medium transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
