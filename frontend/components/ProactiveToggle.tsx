"use client";

import { MessageSquare, MessageSquareOff } from "lucide-react";

interface ProactiveToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
}

export default function ProactiveToggle({
  enabled,
  onToggle,
  disabled = false,
}: ProactiveToggleProps) {
  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border transition-all ${
        disabled
          ? "bg-slate-800/30 border-slate-700/50 opacity-60"
          : "bg-slate-800/50 border-slate-700"
      }`}
    >
      <div className="flex items-center gap-2">
        {enabled ? (
          <MessageSquare className="w-5 h-5 text-green-400" />
        ) : (
          <MessageSquareOff className="w-5 h-5 text-slate-400" />
        )}
        <span className="text-sm text-slate-300">Proactive Greeting</span>
      </div>
      
      <button
        onClick={() => !disabled && onToggle(!enabled)}
        disabled={disabled}
        className={`relative w-11 h-6 rounded-full transition-colors ${
          disabled ? "cursor-not-allowed" : "cursor-pointer"
        } ${enabled ? "bg-green-600" : "bg-slate-600"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
            enabled ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}
